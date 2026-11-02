from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chunk, Document
from app.services.pdf import ExtractedPdf, chunk_text, normalize_text, safe_filename
from tests.conftest import make_pdf


def test_ingestion_page_mapping_and_delete(document_client: TestClient, engine: Engine) -> None:
    data = make_pdf(["First page evidence " * 90, "", "Third page evidence."])
    response = document_client.post(
        "/api/documents", files={"file": ("../report.pdf", data, "application/pdf")}
    )
    assert response.status_code == 201
    doc = response.json()
    assert doc["filename"] == "report.pdf"
    assert doc["status"] == "ready"
    assert doc["page_count"] == 3
    assert doc["empty_page_count"] == 1
    assert doc["chunk_count"] > 2
    assert doc["size_bytes"] == len(data)
    assert document_client.get(f"/api/documents/{doc['id']}").json() == doc
    assert document_client.get("/api/documents").json()["documents"] == [doc]
    with Session(engine) as session:
        chunks = list(session.scalars(select(Chunk).order_by(Chunk.chunk_index)))
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
        assert set(c.page_number for c in chunks) == {1, 3}
        assert all(0 < len(c.content) <= 1000 for c in chunks)
        assert chunks[-1].content == "Third page evidence."
    assert document_client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert document_client.get(f"/api/documents/{doc['id']}").status_code == 404
    assert document_client.delete(f"/api/documents/{doc['id']}").status_code == 404
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 0


@pytest.mark.parametrize(
    "filename,media,data,status",
    [
        ("fake.pdf", "application/pdf", b"not a PDF", 415),
        ("notes.txt", "text/plain", b"hello", 415),
        ("wrong.txt", "application/pdf", make_pdf(["Valid PDF"]), 415),
        ("empty.pdf", "application/pdf", b"", 422),
        ("large.pdf", "application/pdf", b"%PDF-" + b"a" * 20_000, 413),
        ("larger.pdf", "application/pdf", b"%PDF-" + b"a" * 100_000, 413),
    ],
)
def test_invalid_uploads_leave_no_records(
    document_client: TestClient, filename: str, media: str, data: bytes, status: int
) -> None:
    response = document_client.post("/api/documents", files={"file": (filename, data, media)})
    assert response.status_code == status
    assert document_client.get("/api/documents").json()["documents"] == []


@pytest.mark.parametrize(
    "data,error",
    [
        (make_pdf([""]), "No extractable text"),
        (make_pdf([None]), "OCR"),
        (make_pdf([]), "No extractable text"),
        (make_pdf(["Secret"], encrypted=True), "Encrypted"),
        (b"%PDF-1.7\nbroken", "could not be read"),
    ],
)
def test_extraction_failures_are_visible_and_deletable(
    document_client: TestClient, engine: Engine, data: bytes, error: str
) -> None:
    response = document_client.post(
        "/api/documents", files={"file": ("failed.pdf", data, "application/pdf")}
    )
    assert response.status_code == 201
    doc = response.json()
    assert doc["status"] == "failed"
    assert error in doc["error_message"]
    assert doc["chunk_count"] == 0
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert document_client.delete(f"/api/documents/{doc['id']}").status_code == 204


def test_other_workspace_is_not_exposed(document_client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        other = Document(workspace_id=uuid4(), filename="private.pdf", size_bytes=1, status="ready")
        session.add(other)
        session.commit()
        other_id = str(other.id)
    assert document_client.get("/api/documents").json()["documents"] == []
    assert document_client.get(f"/api/documents/{other_id}").status_code == 404
    assert document_client.delete(f"/api/documents/{other_id}").status_code == 404
    with Session(engine) as session:
        assert session.get(Document, UUID(other_id)) is not None


def test_normalization_and_chunk_boundaries() -> None:
    assert normalize_text("  A\x00\tB\n\nＣ  ") == "A B C"
    assert safe_filename("C:\\fakepath\\report.pdf") == "report.pdf"
    text = "x" * 2200
    chunks = chunk_text(text)
    assert [len(c) for c in chunks] == [1000, 1000, 500]
    assert chunks[0][-150:] == chunks[1][:150]
    assert chunk_text("") == []
    with pytest.raises(ValueError):
        chunk_text("text", size=10, overlap=10)


@pytest.mark.parametrize(
    "limit,value,error",
    [
        ("max_pdf_pages", 1, "page limit"),
        ("max_extracted_chars", 3, "text limit"),
    ],
)
def test_extraction_resource_limits(
    document_client: TestClient, settings: Settings, limit: str, value: int, error: str
) -> None:
    setattr(settings, limit, value)
    response = document_client.post(
        "/api/documents",
        files={"file": ("limits.pdf", make_pdf(["First page", "Second page"]), "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert error in response.json()["error_message"]
    assert response.json()["chunk_count"] == 0


def test_chunked_request_limit_before_multipart_parser(document_client: TestClient) -> None:
    response = document_client.post(
        "/api/documents",
        content=(b"x" * 10000 for _ in range(10)),
        headers={"Content-Type": "multipart/form-data; boundary=test"},
    )
    assert response.status_code == 413
    assert document_client.get("/api/documents").json()["documents"] == []


def test_processing_status_is_persisted_before_extraction(
    document_client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.pdf import extract_pdf

    def observe(data: bytes, settings: Settings) -> ExtractedPdf:
        with Session(engine) as session:
            assert session.scalar(select(Document.status)) == "processing"
        return extract_pdf(data, settings)

    monkeypatch.setattr("app.services.documents.extract_pdf", observe)
    response = document_client.post(
        "/api/documents",
        files={"file": ("processing.pdf", make_pdf(["Evidence"]), "application/pdf")},
    )
    assert response.json()["status"] == "ready"
