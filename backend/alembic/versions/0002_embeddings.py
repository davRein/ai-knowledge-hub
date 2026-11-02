"""1536-dimensional embeddings with provider provenance and indexing status."""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "0002_embeddings"
down_revision = "0001_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        if not connection.scalar(sa.text("SELECT 1 FROM pg_extension WHERE extname='vector'")):
            raise RuntimeError(
                "Enable pgvector in this project database as an administrator first."
            )
    op.add_column(
        "chunks",
        sa.Column("embedding", Vector(1536).with_variant(sa.JSON(), "sqlite"), nullable=True),
    )
    op.add_column("chunks", sa.Column("embedding_model", sa.String(120), nullable=True))
    op.add_column(
        "documents",
        sa.Column("embedding_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column("documents", sa.Column("embedding_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "embedding_error")
    op.drop_column("documents", "embedding_status")
    op.drop_column("chunks", "embedding_model")
    op.drop_column("chunks", "embedding")
