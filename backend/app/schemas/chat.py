from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] | None = Field(default=None, max_length=50)

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()


class Citation(BaseModel):
    document_id: UUID
    filename: str
    page: int
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    sources_found: bool
    provider: Literal["fake", "openai"]
    demo: bool
