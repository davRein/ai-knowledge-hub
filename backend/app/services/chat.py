from fastapi import HTTPException

from app.core.config import Settings
from app.providers.base import AIProvider, Evidence, ProviderError, validate_embeddings
from app.repositories.retrieval import RetrievalRepository
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.embeddings import check_vector_schema

NO_EVIDENCE = (
    "I could not find supporting evidence in the selected documents. "
    "Try a more specific question or index your PDFs first."
)


class ChatService:
    def __init__(
        self, repository: RetrievalRepository, settings: Settings, provider: AIProvider
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.provider = provider

    def unsupported(self) -> ChatResponse:
        return ChatResponse(
            answer=NO_EVIDENCE,
            citations=[],
            sources_found=False,
            provider=self.provider.name,
            demo=self.provider.name == "fake",
        )

    def ask(self, request: ChatRequest) -> ChatResponse:
        if request.document_ids is not None:
            if not request.document_ids:
                return self.unsupported()
            if not self.repository.validate_document_ids(request.document_ids):
                raise HTTPException(404, "One or more documents are not in this local workspace.")
        check_vector_schema(self.repository.session)
        vectors = self.provider.embed([request.question])
        validate_embeddings(vectors, 1)
        sources = self.repository.search(
            vectors[0],
            self.provider.profile,
            request.document_ids,
            self.settings.retrieval_top_k,
            self.settings.retrieval_min_similarity,
        )
        if not sources:
            return self.unsupported()
        evidence = [Evidence(str(source.chunk.id), source.chunk.content) for source in sources]
        generated = self.provider.answer(request.question, evidence)
        if not generated.supported:
            return self.unsupported()
        valid = {str(source.chunk.id): source for source in sources}
        if (
            not generated.answer.strip()
            or not generated.source_ids
            or any(source_id not in valid for source_id in generated.source_ids)
        ):
            raise ProviderError(
                "Provider answer failed source validation. No citations were published."
            )
        citations = [
            Citation(
                document_id=valid[source_id].chunk.document_id,
                filename=valid[source_id].filename,
                page=valid[source_id].chunk.page_number,
                excerpt=valid[source_id].chunk.content,
            )
            for source_id in dict.fromkeys(generated.source_ids)
        ]
        return ChatResponse(
            answer=generated.answer,
            citations=citations,
            sources_found=True,
            provider=self.provider.name,
            demo=self.provider.name == "fake",
        )
