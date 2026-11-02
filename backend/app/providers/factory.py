from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.core.access import PrincipalDependency
from app.core.config import Settings
from app.providers.base import AIProvider, ProviderError
from app.providers.fake import FakeProvider


def create_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "fake":
        return FakeProvider()
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value().strip():
        raise ProviderError(
            "AI_PROVIDER=openai requires OPENAI_API_KEY. Use fake for local testing."
        )
    from app.providers.openai import OpenAIProvider

    return OpenAIProvider(
        settings.openai_api_key.get_secret_value(),
        settings.openai_embedding_model,
        settings.openai_answer_model,
    )


def get_provider(request: Request, principal: PrincipalDependency) -> Iterator[AIProvider]:
    # Keep client configuration explicit; tests override this dependency without credentials.
    settings = request.app.state.settings
    if (
        settings.ai_provider == "openai"
        and principal.user is not None
        and not principal.user.external_ai_consent
        and request.method == "POST"
    ):
        raise HTTPException(
            403,
            "External AI consent is required. Enable it in Account before "
            "uploading or asking questions with OpenAI.",
        )
    provider = create_provider(settings)
    try:
        yield provider
    finally:
        if provider.name == "openai":
            from app.providers.openai import OpenAIProvider

            if isinstance(provider, OpenAIProvider):
                provider.client.close()


ProviderDependency = Annotated[AIProvider, Depends(get_provider)]
