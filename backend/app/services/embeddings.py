from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.providers.base import AIProvider, ProviderError, validate_embeddings


def check_vector_schema(session: Session) -> None:
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        column_type = session.scalar(
            text("""
            SELECT format_type(atttypid, atttypmod) FROM pg_attribute
            WHERE attrelid=to_regclass('chunks') AND attname='embedding' AND NOT attisdropped
        """)
        )
        if column_type is None or not column_type.endswith("vector(1536)"):
            raise ProviderError(
                "Database embedding column must be vector(1536). Run M3 migrations."
            )


def index_document(session: Session, document: Document, provider: AIProvider) -> None:
    check_vector_schema(session)
    chunks = list(
        session.scalars(
            select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index)
        )
    )
    if not chunks:
        raise ProviderError("No extracted text is available to index.")
    all_vectors: list[list[float]] = []
    for start in range(0, len(chunks), 32):
        batch = chunks[start : start + 32]
        vectors = provider.embed([chunk.content for chunk in batch])
        validate_embeddings(vectors, len(batch))
        all_vectors.extend(vectors)
    # Apply only after all batches succeeded: never publish a partial index.
    for chunk, vector in zip(chunks, all_vectors, strict=True):
        chunk.embedding = vector
        chunk.embedding_model = provider.profile
    document.embedding_status = "ready"
    document.embedding_error = None


def reindex_workspace(
    session: Session, workspace_id: UUID, provider: AIProvider, owner_id: UUID | None = None
) -> tuple[int, int]:
    documents = list(
        session.scalars(
            select(Document)
            .where(
                Document.workspace_id == workspace_id,
                Document.owner_id == owner_id,
                Document.status == "ready",
            )
            .order_by(Document.id)
        )
    )
    succeeded = failed = 0
    for document in documents:
        try:
            index_document(session, document, provider)
            session.commit()
            succeeded += 1
        except ProviderError as exc:
            session.rollback()
            document.embedding_status = "failed"
            document.embedding_error = str(exc)
            session.commit()
            failed += 1
    return succeeded, failed
