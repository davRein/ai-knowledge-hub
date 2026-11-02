import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.passwords import DUMMY_HASH, hasher, verify_password
from app.models import AuthSession, User
from app.schemas.auth import Credentials, Registration, SessionResponse, UserResponse
from app.services.limits import consume_rate

COOKIE_NAME = "aihub_session"


def cookie_name(settings: Settings) -> str:
    return "__Host-aihub_session" if settings.auth_cookie_secure else COOKIE_NAME


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str, settings: Settings) -> str:
    assert settings.security_key is not None
    return hmac.new(
        settings.security_key.get_secret_value().encode(),
        ("csrf:" + token).encode(),
        hashlib.sha256,
    ).hexdigest()


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def find_user(self, token: str | None) -> User | None:
        if not token or len(token) > 128:
            return None
        return self.session.scalar(
            select(User)
            .join(AuthSession)
            .where(
                AuthSession.token_hash == token_hash(token),
                AuthSession.expires_at > int(time.time()),
            )
        )

    def issue(
        self, user: User, response: Response, old_token: str | None = None
    ) -> SessionResponse:
        self.session.scalar(select(User).where(User.id == user.id).with_for_update())
        if old_token:
            self.session.execute(
                delete(AuthSession).where(AuthSession.token_hash == token_hash(old_token))
            )
        now = int(time.time())
        self.session.execute(
            delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now)
        )
        sessions = list(
            self.session.scalars(
                select(AuthSession)
                .where(AuthSession.user_id == user.id)
                .order_by(AuthSession.created_at.desc())
            )
        )
        for old in sessions[4:]:
            self.session.delete(old)
        token = secrets.token_urlsafe(32)
        seconds = self.settings.session_hours * 3600
        self.session.add(
            AuthSession(
                token_hash=token_hash(token),
                user_id=user.id,
                created_at=now,
                expires_at=now + seconds,
            )
        )
        self.session.commit()
        response.set_cookie(
            cookie_name(self.settings),
            token,
            max_age=seconds,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        return SessionResponse(
            mode="authenticated",
            user=UserResponse.model_validate(user),
            csrf_token=csrf_token(token, self.settings),
            registration_enabled=self.settings.allow_registration,
        )

    def register(self, request: Registration) -> User:
        user = User(
            email=str(request.email).casefold(),
            password_hash=hasher.hash(request.password),
            external_ai_consent=False,
            privacy_accepted_at=int(time.time()),
        )
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise HTTPException(
                409,
                "Registration could not be completed. "
                "Use an existing account or contact the operator.",
            ) from None
        return user

    def login(self, request: Credentials) -> User:
        user = self.session.scalar(
            select(User).where(User.email == str(request.email).casefold()).with_for_update()
        )
        if (
            not verify_password(user.password_hash if user else DUMMY_HASH, request.password)
            or user is None
        ):
            raise HTTPException(401, "Email or password is incorrect.")
        if hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hasher.hash(request.password)
        return user

    def revoke_all(self, user: User) -> None:
        self.session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))

    def confirm_password(self, user: User, password: str) -> User:
        consume_rate(
            self.session,
            self.settings,
            "password-confirm",
            str(user.id),
            self.settings.login_account_per_15min,
            900,
        )
        locked = self.session.scalar(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked is None or not verify_password(locked.password_hash, password):
            raise HTTPException(400, "Current password is incorrect.")
        return locked

    def logout(self, token: str, response: Response) -> None:
        self.session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        self.session.commit()
        response.delete_cookie(
            cookie_name(self.settings),
            path="/",
            secure=self.settings.auth_cookie_secure,
            httponly=True,
            samesite="lax",
        )
