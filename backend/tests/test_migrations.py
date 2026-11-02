from uuid import uuid4

from alembic.config import Config
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from app.models import Chunk, Document


def test_migration_upgrade_downgrade_upgrade(engine: Engine) -> None:
    with engine.connect() as connection:
        schema = (
            connection.scalar(text("SELECT current_schema()"))
            if engine.dialect.name == "postgresql"
            else None
        )
    assert {"documents", "chunks"} <= set(inspect(engine).get_table_names(schema=schema))
    command.downgrade(Config("alembic.ini"), "base")
    assert "documents" not in inspect(engine).get_table_names(schema=schema)
    assert "chunks" not in inspect(engine).get_table_names(schema=schema)
    command.upgrade(Config("alembic.ini"), "head")
    assert {"documents", "chunks"} <= set(inspect(engine).get_table_names(schema=schema))


def test_embedding_migration_preserves_extracted_text(engine: Engine) -> None:
    with Session(engine) as session:
        document = Document(
            workspace_id=uuid4(), filename="migration.pdf", size_bytes=1, status="ready"
        )
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            Chunk(
                document_id=document_id,
                chunk_index=0,
                page_number=2,
                content="Preserved source text.",
            )
        )
        session.commit()
    command.downgrade(Config("alembic.ini"), "0001_documents")
    with Session(engine) as session:
        assert (
            session.scalar(select(Chunk.content).where(Chunk.document_id == document_id))
            == "Preserved source text."
        )
    command.upgrade(Config("alembic.ini"), "head")
    with Session(engine) as session:
        restored = session.get(Document, document_id)
        assert restored is not None and restored.embedding_status == "pending"
