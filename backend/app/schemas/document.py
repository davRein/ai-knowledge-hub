from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: Literal["processing", "ready", "failed"]
    error_message: str | None
    page_count: int
    empty_page_count: int
    chunk_count: int
    embedding_status: Literal["pending", "ready", "failed"]
    embedding_error: str | None
    created_at: datetime


class DocumentListResponse(BaseModel):
    mode: Literal["local-demo", "authenticated"] = "local-demo"
    provider: Literal["fake", "openai"]
    max_upload_bytes: int
    documents: list[DocumentResponse]
