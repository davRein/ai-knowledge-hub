import math
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    filename: str
    score: float


class RetrievalRepository:
    def __init__(self, session: Session, workspace_id: UUID, owner_id: UUID | None = None) -> None:
        self.session = session
        self.workspace_id = workspace_id
        self.owner_id = owner_id

    def validate_document_ids(self, ids: list[UUID]) -> bool:
        owned = set(
            self.session.scalars(
                select(Document.id).where(
                    Document.workspace_id == self.workspace_id,
                    Document.owner_id == self.owner_id,
                    Document.id.in_(ids),
                )
            )
        )
        return owned == set(ids)

    def search(
        self,
        vector: list[float],
        profile: str,
        document_ids: list[UUID] | None,
        top_k: int,
        min_score: float,
    ) -> list[RetrievedChunk]:
        statement = (
            select(Chunk, Document.filename)
            .join(Document)
            .where(
                Document.workspace_id == self.workspace_id,
                Document.owner_id == self.owner_id,
                Document.status == "ready",
                Document.embedding_status == "ready",
                Chunk.embedding.is_not(None),
                Chunk.embedding_model == profile,
            )
        )
        if document_ids is not None:
            statement = statement.where(Document.id.in_(document_ids))
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            # Exact pgvector cosine search. Filter workspace/model/documents BEFORE LIMIT.
            distance = Chunk.embedding.cosine_distance(vector)
            rows = self.session.execute(
                statement.add_columns(distance)
                .where(distance <= 1 - min_score)
                .order_by(distance, Chunk.id)
                .limit(top_k)
            ).all()
            return [
                RetrievedChunk(cast(Chunk, chunk), cast(str, filename), 1 - cast(float, dist))
                for chunk, filename, dist in rows
            ]
        # SQLite is a unit-test fallback, never the production vector store.
        results: list[RetrievedChunk] = []
        for chunk, filename in self.session.execute(statement):
            embedding = chunk.embedding
            if embedding is None:
                continue
            denominator = math.sqrt(sum(v * v for v in vector) * sum(v * v for v in embedding))
            score = (
                sum(a * b for a, b in zip(vector, embedding, strict=True)) / denominator
                if denominator
                else 0
            )
            if score >= min_score:
                results.append(RetrievedChunk(chunk, filename, score))
        return sorted(results, key=lambda result: (-result.score, str(result.chunk.id)))[:top_k]
