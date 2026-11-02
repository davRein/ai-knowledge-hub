from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chunk, Document
from app.providers.base import GroundedAnswer, ProviderError, validate_embeddings
from app.providers.factory import create_provider, get_provider
from app.providers.fake import FakeProvider
from app.services.embeddings import check_vector_schema, index_document, reindex_workspace
from tests.conftest import make_pdf


def upload(client: TestClient, filename: str, pages: list[str | None]) -> dict[str, object]:
    response = client.post(
        "/api/documents", files={"file": (filename, make_pdf(pages), "application/pdf")}
    )
    assert response.status_code == 201
    result: dict[str, object] = response.json()
    assert result["embedding_status"] == "ready"
    return result


def test_retrieval_returns_real_source_page(document_client: TestClient) -> None:
    doc = upload(
        document_client, "handbook.pdf", ["An introduction.", "Annual leave allowance is 25 days."]
    )
    response = document_client.post(
        "/api/chat", json={"question": "What is the annual leave allowance?"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["sources_found"] is True and result["demo"] is True
    assert result["provider"] == "fake"
    assert "25 days" in result["answer"]
    assert result["citations"] == [
        {
            "document_id": doc["id"],
            "filename": "handbook.pdf",
            "page": 2,
            "excerpt": "Annual leave allowance is 25 days.",
        }
    ]


def test_unsupported_question_and_deleted_evidence(document_client: TestClient) -> None:
    doc = upload(document_client, "policy.pdf", ["Annual leave allowance is 25 days."])
    unsupported = document_client.post(
        "/api/chat", json={"question": "Quantum zebra neutron physics?"}
    ).json()
    assert unsupported["sources_found"] is False
    assert unsupported["citations"] == []
    assert "could not find supporting evidence" in unsupported["answer"]
    document_client.delete(f"/api/documents/{doc['id']}")
    result = document_client.post("/api/chat", json={"question": "Annual leave allowance?"}).json()
    assert result["sources_found"] is False and result["citations"] == []


def test_document_filter_and_empty_selection(document_client: TestClient) -> None:
    first = upload(document_client, "leave.pdf", ["Annual leave allowance is 25 days."])
    second = upload(document_client, "travel.pdf", ["Travel reimbursement requires a receipt."])
    query = {"question": "Annual leave allowance?", "document_ids": [second["id"]]}
    assert document_client.post("/api/chat", json=query).json()["sources_found"] is False
    query["document_ids"] = [first["id"]]
    result = document_client.post("/api/chat", json=query).json()
    assert result["sources_found"] is True
    assert {c["document_id"] for c in result["citations"]} == {first["id"]}
    query["document_ids"] = []
    assert document_client.post("/api/chat", json=query).json()["citations"] == []


def test_other_workspace_is_never_retrieved(document_client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        other = Document(
            workspace_id=uuid4(),
            filename="private.pdf",
            size_bytes=1,
            status="ready",
            embedding_status="ready",
        )
        session.add(other)
        session.flush()
        provider = FakeProvider()
        session.add(
            Chunk(
                document_id=other.id,
                chunk_index=0,
                page_number=42,
                content="Classified launch code is secret.",
                embedding=provider.embed(["Classified launch code is secret."])[0],
                embedding_model=provider.profile,
            )
        )
        session.commit()
        other_id = str(other.id)
    query = {"question": "Classified launch code?"}
    result = document_client.post("/api/chat", json=query).json()
    assert result["sources_found"] is False
    assert result["citations"] == []
    assert (
        document_client.post("/api/chat", json={**query, "document_ids": [other_id]}).status_code
        == 404
    )
    assert (
        document_client.post(
            "/api/chat", json={**query, "document_ids": [str(uuid4())]}
        ).status_code
        == 404
    )


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_question_validation(document_client: TestClient, question: str) -> None:
    assert document_client.post("/api/chat", json={"question": question}).status_code == 422


def test_no_automatic_openai_activation() -> None:
    config = Settings(_env_file=None, ai_provider="fake", openai_api_key="unused-test-key")
    assert create_provider(config).name == "fake"
    with pytest.raises(ProviderError, match="requires OPENAI_API_KEY"):
        create_provider(Settings(_env_file=None, ai_provider="openai", openai_api_key=None))


@pytest.mark.parametrize(
    "vector", [[1.0], [float("nan")] * 1536, [float("inf")] * 1536, [0.0] * 1536]
)
def test_embedding_validation(vector: list[float]) -> None:
    with pytest.raises(ProviderError):
        validate_embeddings([vector], 1)


def test_fake_provider_is_deterministic() -> None:
    assert FakeProvider().embed(["Annual leave allowance"]) == FakeProvider().embed(
        ["Annual leave allowance"]
    )


def test_invented_source_is_rejected(document_client: TestClient) -> None:
    upload(document_client, "leave.pdf", ["Annual leave allowance is 25 days."])

    class InventingProvider(FakeProvider):
        def answer(self, question: str, evidence: object) -> GroundedAnswer:
            return GroundedAnswer(supported=True, answer="Invented!", source_ids=["not-retrieved"])

    cast(FastAPI, document_client.app).dependency_overrides[get_provider] = InventingProvider
    response = document_client.post("/api/chat", json={"question": "Annual leave allowance?"})
    assert response.status_code == 503
    assert "source validation" in response.json()["detail"]
    assert "Invented!" not in response.text


def test_provider_abstention_has_no_citations(document_client: TestClient) -> None:
    upload(document_client, "leave.pdf", ["Annual leave allowance is 25 days."])

    class AbstainingProvider(FakeProvider):
        def answer(self, question: str, evidence: object) -> GroundedAnswer:
            return GroundedAnswer(supported=False, answer="Ignore this", source_ids=["anything"])

    cast(FastAPI, document_client.app).dependency_overrides[get_provider] = AbstainingProvider
    result = document_client.post("/api/chat", json={"question": "Annual leave allowance?"}).json()
    assert result["sources_found"] is False and result["citations"] == []
    assert "Ignore this" not in result["answer"]


def test_embedding_failure_is_visible_and_reindexable(
    document_client: TestClient, engine: Engine, settings: Settings
) -> None:
    class BadProvider(FakeProvider):
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] for _ in texts]

    cast(FastAPI, document_client.app).dependency_overrides[get_provider] = BadProvider
    result = document_client.post(
        "/api/documents",
        files={
            "file": (
                "failed-index.pdf",
                make_pdf(["Annual leave allowance is 25 days."]),
                "application/pdf",
            )
        },
    ).json()
    assert result["status"] == "ready" and result["embedding_status"] == "failed"
    assert "dimension" in result["embedding_error"]
    with Session(engine) as session:
        assert session.scalar(select(Chunk.embedding)) is None
        assert reindex_workspace(session, settings.local_workspace_id, FakeProvider()) == (1, 0)
    cast(FastAPI, document_client.app).dependency_overrides.pop(get_provider)
    assert (
        document_client.post("/api/chat", json={"question": "Annual leave allowance?"}).json()[
            "sources_found"
        ]
        is True
    )


def test_incompatible_model_vectors_are_not_retrieved(
    document_client: TestClient, engine: Engine
) -> None:
    upload(document_client, "leave.pdf", ["Annual leave allowance is 25 days."])
    with Session(engine) as session:
        chunk = session.scalar(select(Chunk))
        assert chunk is not None
        chunk.embedding_model = "other:model:1536"
        session.commit()
    assert (
        document_client.post("/api/chat", json={"question": "Annual leave allowance?"}).json()[
            "sources_found"
        ]
        is False
    )


def test_batch_failure_never_publishes_partial_vectors(engine: Engine, settings: Settings) -> None:
    class SecondBatchFails(FakeProvider):
        calls = 0

        def embed(self, texts: list[str]) -> list[list[float]]:
            self.calls += 1
            if self.calls == 2:
                raise ProviderError("Simulated second batch failure")
            return super().embed(texts)

    with Session(engine) as session:
        document = Document(
            workspace_id=settings.local_workspace_id,
            filename="batch.pdf",
            size_bytes=1,
            status="ready",
        )
        session.add(document)
        session.flush()
        session.add_all(
            [
                Chunk(
                    document_id=document.id,
                    chunk_index=i,
                    page_number=1,
                    content="Annual leave allowance",
                )
                for i in range(35)
            ]
        )
        session.commit()
        with pytest.raises(ProviderError, match="second batch"):
            index_document(session, document, SecondBatchFails())
        assert all(chunk.embedding is None for chunk in session.scalars(select(Chunk)))
        assert document.embedding_status == "pending"


def test_database_dimension_mismatch_is_rejected(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Actual pgvector schema check needs PostgreSQL")
    from sqlalchemy import text

    with engine.begin() as connection:
        # Fixture verified that chunks resolves to its disposable test schema.
        connection.execute(
            text("ALTER TABLE chunks ALTER COLUMN embedding TYPE public.vector(3) USING NULL")
        )
    with Session(engine) as session:
        with pytest.raises(ProviderError, match="vector\\(1536\\)"):
            check_vector_schema(session)
