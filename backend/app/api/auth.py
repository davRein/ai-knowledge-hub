from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import delete, func, select

from app.core.access import PrincipalDependency, require_origin
from app.core.passwords import hasher
from app.db.session import SessionDependency, SettingsDependency
from app.models import Document, User
from app.schemas.auth import (
    ConsentRequest,
    Credentials,
    PasswordChange,
    PasswordConfirmation,
    Registration,
    SessionResponse,
    UserResponse,
)
from app.services.auth import AuthService, cookie_name, csrf_token
from app.services.limits import consume_rate

router = APIRouter(tags=["authentication"])


def auth_mode(settings: SettingsDependency) -> None:
    if settings.app_mode != "authenticated":
        raise HTTPException(404, "Authentication is disabled in local-demo mode.")


@router.get("/api/auth/session", response_model=SessionResponse)
def current_session(
    request: Request, session: SessionDependency, settings: SettingsDependency
) -> SessionResponse:
    if settings.app_mode == "local-demo":
        return SessionResponse(mode="local-demo")
    user = AuthService(session, settings).find_user(request.cookies.get(cookie_name(settings)))
    return SessionResponse(
        mode="authenticated",
        user=UserResponse.model_validate(user) if user else None,
        csrf_token=csrf_token(request.cookies[cookie_name(settings)], settings) if user else None,
        registration_enabled=settings.allow_registration,
    )


@router.post("/api/auth/register", response_model=SessionResponse, status_code=201)
def register(
    payload: Registration,
    request: Request,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SessionResponse:
    auth_mode(settings)
    require_origin(request, settings)
    if not settings.allow_registration:
        raise HTTPException(403, "Registration is closed. Contact the operator for an account.")
    consume_rate(
        session,
        settings,
        "register",
        request.client.host if request.client else "unknown",
        settings.login_ip_per_minute,
        60,
    )
    service = AuthService(session, settings)
    user = service.register(payload)
    return service.issue(user, response, request.cookies.get(cookie_name(settings)))


@router.post("/api/auth/login", response_model=SessionResponse)
def login(
    payload: Credentials,
    request: Request,
    response: Response,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SessionResponse:
    auth_mode(settings)
    require_origin(request, settings)
    consume_rate(
        session,
        settings,
        "login-ip",
        request.client.host if request.client else "unknown",
        settings.login_ip_per_minute,
        60,
    )
    consume_rate(
        session,
        settings,
        "login-account",
        str(payload.email).casefold(),
        settings.login_account_per_15min,
        900,
    )
    service = AuthService(session, settings)
    return service.issue(
        service.login(payload), response, request.cookies.get(cookie_name(settings))
    )


@router.post("/api/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    principal: PrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> Response:
    auth_mode(settings)
    AuthService(session, settings).logout(request.cookies[cookie_name(settings)], response)
    response.status_code = 204
    return response


@router.get("/api/account")
def account(
    principal: PrincipalDependency, session: SessionDependency, settings: SettingsDependency
) -> dict[str, object]:
    auth_mode(settings)
    assert principal.user is not None
    count, size = session.execute(
        select(func.count(Document.id), func.coalesce(func.sum(Document.size_bytes), 0)).where(
            Document.owner_id == principal.owner_id
        )
    ).one()
    return {
        "user": UserResponse.model_validate(principal.user),
        "usage": {"documents": count, "bytes": size},
        "limits": {
            "documents": settings.max_documents_per_user,
            "bytes": settings.max_storage_bytes_per_user,
        },
    }


@router.patch("/api/account/consent", response_model=UserResponse)
def consent(
    payload: ConsentRequest,
    principal: PrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> UserResponse:
    auth_mode(settings)
    assert principal.user is not None
    principal.user.external_ai_consent = payload.accepted
    session.commit()
    return UserResponse.model_validate(principal.user)


@router.post("/api/account/password", response_model=SessionResponse)
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    principal: PrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> SessionResponse:
    auth_mode(settings)
    assert principal.user is not None
    service = AuthService(session, settings)
    user = service.confirm_password(principal.user, payload.password)
    user.password_hash = hasher.hash(payload.new_password)
    service.revoke_all(user)
    return service.issue(user, response)


@router.delete("/api/account", status_code=204)
def delete_account(
    payload: PasswordConfirmation,
    response: Response,
    principal: PrincipalDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> Response:
    auth_mode(settings)
    assert principal.user is not None
    AuthService(session, settings).confirm_password(principal.user, payload.password)
    session.execute(delete(User).where(User.id == principal.owner_id))
    session.commit()
    response.delete_cookie(
        cookie_name(settings),
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.status_code = 204
    return response
