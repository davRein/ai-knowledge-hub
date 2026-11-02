import math
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

EMBEDDING_DIMENSIONS = 1536


class ProviderError(RuntimeError):
    """Safe provider/configuration failure; never include provider request contents."""


@dataclass(frozen=True)
class Evidence:
    source_id: str
    text: str


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    answer: str
    source_ids: list[str]


class AIProvider(Protocol):
    name: str
    profile: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def answer(self, question: str, evidence: list[Evidence]) -> GroundedAnswer: ...


def validate_embeddings(vectors: list[list[float]], count: int) -> None:
    if len(vectors) != count:
        raise ProviderError("Embedding provider returned an incorrect batch size.")
    for vector in vectors:
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ProviderError("Embedding dimension does not match the 1536-dimension schema.")
        if not all(math.isfinite(value) and abs(value) <= 3.4e38 for value in vector):
            raise ProviderError("Embedding provider returned non-finite values.")
        if sum(value * value for value in vector) == 0:
            raise ProviderError("Embedding provider returned a zero vector.")
