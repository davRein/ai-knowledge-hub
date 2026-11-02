import hmac
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings
from app.db.session import SessionDependency, SettingsDependency
from app.models import User
from app.services.auth import AuthService, cookie_name, csrf_token
from app.services.limits import consume_rate


@dataclass(frozen=True)
class Principal:
    workspace_id: UUID
    user: User | None = None

    @property
    def owner_id(self) -> UUID | None:
        return self.user.id if self.user is not None else None


def require_origin(request: Request, settings: Settings) -> None:
    if request.headers.get("origin") not in settings.cors_origins:
        raise HTTPException(403, "Request origin is not allowed.")


def get_principal(
    request: Request, session: SessionDependency, settings: SettingsDependency
) -> Principal:
    if settings.app_mode == "local-demo":
        return Principal(settings.local_workspace_id)
    token = request.cookies.get(cookie_name(settings))
    user = AuthService(session, settings).find_user(token)
    if user is None:
        raise HTTPException(401, "Sign in to access your workspace.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_origin(request, settings)
        expected = csrf_token(token or "", settings)
        actual = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(actual.encode(), expected.encode()):
            raise HTTPException(403, "Session protection check failed. Refresh and try again.")
    identity = str(user.id)
    consume_rate(session, settings, "api", identity, settings.requests_per_minute, 60)
    if request.method == "POST" and request.url.path.rstrip("/") == "/api/chat":
        consume_rate(session, settings, "chat", identity, settings.chat_per_minute, 60)
    if request.method == "POST" and request.url.path.rstrip("/") == "/api/documents":
        consume_rate(session, settings, "upload", identity, settings.uploads_per_hour, 3600)
    return Principal(user.id, user)


PrincipalDependency = Annotated[Principal, Depends(get_principal)]
