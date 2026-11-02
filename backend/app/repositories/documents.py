from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chunk, Document, User


class DocumentRepository:
    def __init__(
        self,
        session: Session,
        workspace_id: UUID,
        owner_id: UUID | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.workspace_id = workspace_id
        self.owner_id = owner_id
        self.settings = settings

    def list_documents(self) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document)
                .where(
                    Document.workspace_id == self.workspace_id, Document.owner_id == self.owner_id
                )
                .order_by(Document.created_at.desc(), Document.id.desc())
            )
        )

    def get(self, document_id: UUID) -> Document | None:
        return self.session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == self.workspace_id,
                Document.owner_id == self.owner_id,
            )
        )

    def create(self, filename: str, size: int) -> Document:
        if self.owner_id and self.settings:
            self.session.scalar(select(User).where(User.id == self.owner_id).with_for_update())
            count, total = self.session.execute(
                select(
                    func.count(Document.id), func.coalesce(func.sum(Document.size_bytes), 0)
                ).where(Document.owner_id == self.owner_id)
            ).one()
            if (
                count >= self.settings.max_documents_per_user
                or total + size > self.settings.max_storage_bytes_per_user
            ):
                raise HTTPException(
                    409, "Document quota reached. Delete unused documents before uploading more."
                )
        document = Document(
            workspace_id=self.workspace_id,
            owner_id=self.owner_id,
            filename=filename,
            size_bytes=size,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def add_chunks(self, document: Document, chunks: list[tuple[int, str]]) -> None:
        if self.owner_id and self.settings:
            self.session.scalar(select(User).where(User.id == self.owner_id).with_for_update())
            count = (
                self.session.scalar(
                    select(func.count(Chunk.id))
                    .join(Document)
                    .where(Document.owner_id == self.owner_id)
                )
                or 0
            )
            if count + len(chunks) > self.settings.max_chunks_per_user:
                from app.services.pdf import PdfError

                raise PdfError("Extracted text quota reached. Delete unused documents and retry.")
        self.session.add_all(
            [
                Chunk(document_id=document.id, chunk_index=index, page_number=page, content=content)
                for index, (page, content) in enumerate(chunks)
            ]
        )

    def delete(self, document_id: UUID) -> bool:
        result = self.session.execute(
            delete(Document)
            .where(
                Document.id == document_id,
                Document.workspace_id == self.workspace_id,
                Document.owner_id == self.owner_id,
            )
            .returning(Document.id)
        )
        deleted = result.scalar_one_or_none() is not None
        self.session.commit()
        return deleted
