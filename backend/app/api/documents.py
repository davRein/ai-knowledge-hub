from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile

from app.core.access import PrincipalDependency
from app.db.session import SessionDependency, SettingsDependency
from app.providers.factory import ProviderDependency
from app.repositories.documents import DocumentRepository
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.documents import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_service(
    session: SessionDependency,
    settings: SettingsDependency,
    provider: ProviderDependency,
    principal: PrincipalDependency,
) -> DocumentService:
    return DocumentService(
        DocumentRepository(session, principal.workspace_id, principal.owner_id, settings),
        settings,
        provider,
    )


ServiceDependency = Annotated[DocumentService, Depends(get_service)]


@router.get("", response_model=DocumentListResponse)
def list_documents(service: ServiceDependency) -> DocumentListResponse:
    return DocumentListResponse(
        mode=service.settings.app_mode,
        provider=service.provider.name,
        max_upload_bytes=service.settings.max_upload_bytes,
        documents=[
            DocumentResponse.model_validate(doc) for doc in service.repository.list_documents()
        ],
    )


@router.post("", response_model=DocumentResponse, status_code=201)
def upload_document(
    service: ServiceDependency, file: Annotated[UploadFile, File()]
) -> DocumentResponse:
    """Ingest synchronously. A persisted extraction failure returns status=failed (201)."""
    data = file.file.read(service.settings.max_upload_bytes + 1)
    return DocumentResponse.model_validate(service.ingest(data, file.filename, file.content_type))


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, service: ServiceDependency) -> DocumentResponse:
    return DocumentResponse.model_validate(service.get(document_id))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, service: ServiceDependency) -> Response:
    service.delete(document_id)
    return Response(status_code=204)
