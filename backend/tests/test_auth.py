import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app
from app.models import AuthSession, Chunk, Document, User
from tests.conftest import make_pdf

ORIGIN = "http://127.0.0.1:3000"
PASSWORD = "a long test password 123!"


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_mode="authenticated",
        security_key="a" * 48,
        allow_registration=True,
        database_url="sqlite://",
    )


@pytest.fixture
def clients(engine: Engine, auth_settings: Settings) -> Iterator[tuple[TestClient, TestClient]]:
    app = create_app(auth_settings)

    def override() -> Iterator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override
    with (
        TestClient(app, headers={"Origin": ORIGIN}) as a,
        TestClient(app, headers={"Origin": ORIGIN}) as b,
    ):
        yield a, b


def register(client: TestClient, email: str = "alice@example.com") -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "accepted_privacy": True,
        },
    )
    assert response.status_code == 201, response.text
    data: dict[str, object] = response.json()
    client.headers["X-CSRF-Token"] = str(data["csrf_token"])
    return data


def upload(client: TestClient) -> str:
    response = client.post(
        "/api/documents",
        files={
            "file": (
                "Policy.pdf",
                make_pdf(["Annual leave allowance is 25 days."]),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_private_documents_retrieval_and_delete(clients: tuple[TestClient, TestClient]) -> None:
    a, b = clients
    assert a.get("/api/documents").status_code == 401
    register(a)
    register(b, "bob@example.com")
    doc = upload(a)
    assert len(a.get("/api/documents").json()["documents"]) == 1
    assert b.get("/api/documents").json()["documents"] == []
    assert b.get(f"/api/documents/{doc}").status_code == 404
    assert b.delete(f"/api/documents/{doc}").status_code == 404
    blocked = b.post("/api/chat", json={"question": "Annual leave?", "document_ids": [doc]})
    assert blocked.status_code == 404
    empty = b.post("/api/chat", json={"question": "Annual leave?"})
    assert empty.status_code == 200
    assert empty.json()["sources_found"] is False
    answer = a.post("/api/chat", json={"question": "Annual leave?", "document_ids": [doc]})
    assert answer.status_code == 200, answer.text
    assert answer.json()["citations"][0]["document_id"] == doc
    assert a.delete(f"/api/documents/{doc}").status_code == 204


def test_csrf_origin_and_cookie(clients: tuple[TestClient, TestClient]) -> None:
    a, _ = clients
    response = a.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "accepted_privacy": True},
    )
    assert response.status_code == 201
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert a.post("/api/auth/logout").status_code == 403
    a.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert a.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert a.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert a.get("/api/documents").status_code == 200
    assert a.post("/api/auth/logout").status_code == 204
    assert a.get("/api/documents").status_code == 401


def test_session_hash_expiry_password_rotation(
    clients: tuple[TestClient, TestClient], engine: Engine
) -> None:
    a, b = clients
    register(a)
    login = b.post("/api/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD})
    assert login.status_code == 200
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user is not None and user.password_hash.startswith("$argon2id$")
        tokens = db.scalars(select(AuthSession.token_hash)).all()
        assert a.cookies["aihub_session"] not in tokens
    changed = a.post(
        "/api/account/password", json={"password": PASSWORD, "new_password": PASSWORD + "new"}
    )
    assert changed.status_code == 200
    assert b.get("/api/documents").status_code == 401
    assert a.get("/api/documents").status_code == 200
    assert (
        b.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )
    with Session(engine) as db:
        db.execute(update(AuthSession).values(expires_at=int(time.time()) - 1))
        db.commit()
    assert a.get("/api/documents").status_code == 401


def test_account_deletion_cascades_only_own_data(
    clients: tuple[TestClient, TestClient], engine: Engine
) -> None:
    a, b = clients
    register(a)
    register(b, "bob@example.com")
    upload(a)
    other = upload(b)
    assert a.request("DELETE", "/api/account", json={"password": "wrong"}).status_code == 400
    assert a.request("DELETE", "/api/account", json={"password": PASSWORD}).status_code == 204
    assert a.get("/api/documents").status_code == 401
    assert b.get(f"/api/documents/{other}").status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(func.count(User.id))) == 1
        assert db.scalar(select(func.count(Document.id))) == 1
        assert db.scalar(select(func.count(Chunk.id))) == 1
        assert db.scalar(select(func.count(AuthSession.token_hash))) == 1


def test_document_quota_freed_by_deletion(
    clients: tuple[TestClient, TestClient], auth_settings: Settings
) -> None:
    a, _ = clients
    auth_settings.max_documents_per_user = 1
    register(a)
    doc = upload(a)
    response = a.post(
        "/api/documents", files={"file": ("x.pdf", make_pdf(["More text"]), "application/pdf")}
    )
    assert response.status_code == 409
    assert a.get("/api/account").json()["usage"]["documents"] == 1
    a.delete(f"/api/documents/{doc}")
    upload(a)


def test_limits_and_validation_do_not_echo_credentials(
    clients: tuple[TestClient, TestClient], auth_settings: Settings
) -> None:
    a, _ = clients
    auth_settings.login_account_per_15min = 1
    bad = {"email": "missing@example.com", "password": PASSWORD}
    assert a.post("/api/auth/login", json=bad).status_code == 401
    limited = a.post("/api/auth/login", json=bad)
    assert limited.status_code == 429 and int(limited.headers["retry-after"]) > 0
    invalid = a.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "short", "accepted_privacy": True},
    )
    assert invalid.status_code == 422
    assert all("input" not in item for item in invalid.json()["detail"])
    too_large = a.post("/api/auth/login", content="x" * 17000)
    assert too_large.status_code == 413


def test_external_ai_requires_explicit_consent(
    clients: tuple[TestClient, TestClient], auth_settings: Settings
) -> None:
    a, _ = clients
    register(a)
    auth_settings.ai_provider = "openai"
    blocked = a.post("/api/chat", json={"question": "Annual leave?"})
    assert blocked.status_code == 403 and "consent" in blocked.text
    assert (
        a.patch("/api/account/consent", json={"accepted": True}).json()["external_ai_consent"]
        is True
    )
    assert (
        a.patch("/api/account/consent", json={"accepted": False}).json()["external_ai_consent"]
        is False
    )


def test_legacy_demo_is_never_claimed_on_registration(
    clients: tuple[TestClient, TestClient], engine: Engine, auth_settings: Settings
) -> None:
    with Session(engine) as db:
        db.add(
            Document(
                workspace_id=auth_settings.local_workspace_id, filename="legacy.pdf", size_bytes=100
            )
        )
        db.commit()
    a, _ = clients
    register(a)
    assert a.get("/api/documents").json()["documents"] == []
    with Session(engine) as db:
        assert db.scalar(select(Document.owner_id)) is None


def test_closed_registration_and_security_headers(
    clients: tuple[TestClient, TestClient], auth_settings: Settings
) -> None:
    a, _ = clients
    auth_settings.allow_registration = False
    assert (
        a.post(
            "/api/auth/register",
            json={"email": "alice@example.com", "password": PASSWORD, "accepted_privacy": True},
        ).status_code
        == 403
    )
    response = a.get("/api/auth/session")
    assert response.json()["registration_enabled"] is False
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert len(response.headers["x-request-id"]) == 32
    assert a.get("/health", headers={"Host": "evil.example"}).status_code == 400


def test_production_configuration_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_mode="authenticated")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["https://*.example.com"])
    settings = Settings(
        _env_file=None,
        app_mode="authenticated",
        app_env="production",
        security_key="s" * 48,
        auth_cookie_secure=True,
        allow_registration=False,
        cors_origins=["https://hub.example.com"],
        allowed_hosts=["api.example.com"],
        database_url="postgresql+psycopg://user:unique@db.example.com/hub",
    )
    with TestClient(create_app(settings), base_url="https://api.example.com") as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
