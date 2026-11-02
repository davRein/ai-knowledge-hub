from fastapi import APIRouter

from app.db.session import SettingsDependency
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDependency) -> HealthResponse:
    """Process liveness only; does not check PostgreSQL or an AI provider."""
    return HealthResponse(mode=settings.app_mode)
