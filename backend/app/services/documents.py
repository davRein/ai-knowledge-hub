from uuid import UUID

from fastapi import HTTPException

from app.core.config import Settings
from app.models import Document
from app.providers.base import AIProvider, ProviderError
from app.repositories.documents import DocumentRepository
from app.services.embeddings import index_document
from app.services.pdf import PdfError, extract_pdf, safe_filename


class DocumentService:
    def __init__(
        self, repository: DocumentRepository, settings: Settings, provider: AIProvider
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.provider = provider

    def get(self, document_id: UUID) -> Document:
        document = self.repository.get(document_id)
        if document is None:
            raise HTTPException(404, "Document not found in this local workspace.")
        return document

    def ingest(self, data: bytes, filename: str | None, content_type: str | None) -> Document:
        if len(data) > self.settings.max_upload_bytes:
            raise HTTPException(413, "PDF exceeds the configured upload size limit.")
        if not data:
            raise HTTPException(422, "The uploaded file is empty.")
        name = safe_filename(filename)
        if (
            not name.lower().endswith(".pdf")
            or content_type not in {"application/pdf", "application/octet-stream"}
            or not data.startswith(b"%PDF-")
        ):
            raise HTTPException(415, "Upload a PDF with a valid PDF signature and .pdf filename.")
        document = self.repository.create(name, len(data))
        try:
            extracted = extract_pdf(data, self.settings)
            document.page_count = extracted.page_count
            document.empty_page_count = extracted.empty_page_count
            if not extracted.chunks:
                raise PdfError(
                    "No extractable text found. Empty/scanned PDFs need OCR, "
                    "which is not supported."
                )
            self.repository.add_chunks(document, extracted.chunks)
            document.chunk_count = len(extracted.chunks)
            document.status = "ready"
        except PdfError as exc:
            document.status = "failed"
            document.error_message = str(exc)
        self.repository.session.commit()
        if document.status == "ready":
            try:
                index_document(self.repository.session, document, self.provider)
            except ProviderError as exc:
                document.embedding_status = "failed"
                document.embedding_error = str(exc)
            self.repository.session.commit()
        self.repository.session.refresh(document)
        return document

    def delete(self, document_id: UUID) -> None:
        self.get(document_id)
        if not self.repository.delete(document_id):
            raise HTTPException(404, "Document not found in this local workspace.")
