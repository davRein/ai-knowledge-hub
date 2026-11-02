from fastapi import APIRouter

from app.core.access import PrincipalDependency
from app.db.session import SessionDependency, SettingsDependency
from app.providers.factory import ProviderDependency
from app.repositories.retrieval import RetrievalRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    provider: ProviderDependency,
    principal: PrincipalDependency,
) -> ChatResponse:
    """Grounded single-turn answer. Fake mode is explicitly labeled; no chat is persisted."""
    return ChatService(
        RetrievalRepository(session, principal.workspace_id, principal.owner_id), settings, provider
    ).ask(request)
