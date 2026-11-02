from uuid import uuid4

from alembic.config import Config
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.manage import claim_demo
from app.models import Chunk, Document
from app.schemas.auth import Registration
from app.services.auth import AuthService


def test_auth_upgrade_preserves_existing_document_and_chunk(engine: Engine) -> None:
    # This fixture points exclusively to a disposable test database/schema.
    command.downgrade(Config("alembic.ini"), "0002_embeddings")
    doc_id, chunk_id, workspace = uuid4(), uuid4(), uuid4()

    def identifier(value: object) -> object:
        return str(value).replace("-", "") if engine.dialect.name == "sqlite" else value

    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO documents (id,workspace_id,filename,content_type,size_bytes,status,"
                "page_count,empty_page_count,chunk_count,embedding_status) VALUES "
                "(:id,:workspace,'preserved.pdf','application/pdf',100,'ready',2,0,1,'pending')"
            ),
            {"id": identifier(doc_id), "workspace": identifier(workspace)},
        )
        db.execute(
            text(
                "INSERT INTO chunks (id,document_id,chunk_index,page_number,content) "
                "VALUES (:id,:doc,0,2,'Preserved original text')"
            ),
            {"id": identifier(chunk_id), "doc": identifier(doc_id)},
        )
    command.upgrade(Config("alembic.ini"), "head")
    with Session(engine) as session:
        document = session.get(Document, doc_id)
        chunk = session.get(Chunk, chunk_id)
        assert document is not None and document.owner_id is None
        assert document.workspace_id == workspace and document.filename == "preserved.pdf"
        assert (
            chunk is not None
            and chunk.page_number == 2
            and chunk.content == "Preserved original text"
        )


def test_demo_claim_is_explicit_and_preserves_chunks(engine: Engine) -> None:
    settings = Settings(_env_file=None, database_url="sqlite://")
    with Session(engine, expire_on_commit=False) as db:
        user = AuthService(db, settings).register(
            Registration(
                email="owner@example.com",
                password="a long password for tests",
                accepted_privacy=True,
            )
        )
        legacy = Document(
            workspace_id=settings.local_workspace_id, filename="old.pdf", size_bytes=100
        )
        db.add(legacy)
        db.flush()
        db.add(
            Chunk(
                document_id=legacy.id, chunk_index=0, page_number=3, content="Original legacy text"
            )
        )
        db.commit()
        assert claim_demo(db, settings, user, False) == 1
        db.refresh(legacy)
        assert legacy.owner_id is None
        assert claim_demo(db, settings, user, True) == 1
        db.refresh(legacy)
        assert legacy.owner_id == user.id and legacy.workspace_id == user.id
        assert db.scalar(select(Chunk.page_number).where(Chunk.document_id == legacy.id)) == 3
