import json
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chunk, Document
from app.providers.fake import FakeProvider
from app.repositories.retrieval import RetrievalRepository
from app.schemas.auth import Registration
from app.schemas.chat import ChatRequest
from app.seed_demo import SAMPLE_PDF, seed_sample
from app.services.auth import AuthService
from app.services.chat import ChatService


def test_seed_preview_repeatability_and_sample_questions(engine: Engine) -> None:
    settings = Settings(_env_file=None, database_url="sqlite://")
    with Session(engine, expire_on_commit=False) as db:
        assert seed_sample(db, settings).status == "preview"
        assert db.scalar(select(func.count(Document.id))) == 0
        created = seed_sample(db, settings, confirm=True)
        assert created.status == "created" and created.document_id is not None
        repeated = seed_sample(db, settings, confirm=True)
        assert repeated.status == "existing" and repeated.document_id == created.document_id
        assert db.scalar(select(func.count(Document.id))) == 1
        assert db.scalar(select(func.count(Chunk.id))) == 3
        source = json.loads(SAMPLE_PDF.with_suffix(".json").read_text(encoding="utf-8"))
        chat = ChatService(
            RetrievalRepository(db, settings.local_workspace_id), settings, FakeProvider()
        )
        for example in source["questions"]:
            result = chat.ask(
                ChatRequest(question=example["question"], document_ids=[created.document_id])
            )
            if example["page"] is None:
                assert not result.sources_found and not result.citations
            else:
                assert result.sources_found and example["answer_contains"] in result.answer
                assert {citation.page for citation in result.citations} == {example["page"]}


def test_seed_requires_owner_and_never_claims_legacy(engine: Engine) -> None:
    settings = Settings(
        _env_file=None, database_url="sqlite://", app_mode="authenticated", security_key="s" * 48
    )
    with Session(engine, expire_on_commit=False) as db:
        legacy = Document(
            workspace_id=settings.local_workspace_id, filename="legacy.pdf", size_bytes=100
        )
        foreign = Document(workspace_id=uuid4(), filename="foreign.pdf", size_bytes=100)
        db.add_all([legacy, foreign])
        db.commit()
        user = AuthService(db, settings).register(
            Registration(
                email="demo@example.com",
                password="synthetic password for tests",
                accepted_privacy=True,
            )
        )
        with pytest.raises(ValueError, match="existing account"):
            seed_sample(db, settings, confirm=True)
        with pytest.raises(ValueError, match="does not exist"):
            seed_sample(db, settings, "missing@example.com", confirm=True)
        result = seed_sample(db, settings, user.email, confirm=True)
        doc = db.get(Document, result.document_id)
        assert doc is not None and doc.owner_id == user.id and doc.workspace_id == user.id
        db.refresh(legacy)
        db.refresh(foreign)
        assert legacy.owner_id is None and foreign.owner_id is None
        assert db.scalar(select(func.count(Document.id))) == 3


@pytest.mark.parametrize("changes", [{"app_env": "production"}, {"ai_provider": "openai"}])
def test_seed_refuses_production_and_external_ai(engine: Engine, changes: dict[str, str]) -> None:
    settings = Settings(_env_file=None, database_url="sqlite://").model_copy(update=changes)
    with Session(engine) as db:
        with pytest.raises(ValueError, match="development mode"):
            seed_sample(db, settings, confirm=True)
        assert db.scalar(select(func.count(Document.id))) == 0


def test_seed_does_not_overwrite_filename_collision(engine: Engine) -> None:
    settings = Settings(_env_file=None, database_url="sqlite://")
    with Session(engine, expire_on_commit=False) as db:
        existing = Document(
            workspace_id=settings.local_workspace_id, filename=SAMPLE_PDF.name, size_bytes=100
        )
        db.add(existing)
        db.commit()
        with pytest.raises(ValueError, match="incompatible"):
            seed_sample(db, settings, confirm=True)
        assert db.get(Document, existing.id) is existing
        assert db.scalar(select(func.count(Document.id))) == 1
