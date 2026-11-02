import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None)))


def test_health_contract(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local-demo"}


def test_openapi_contains_only_current_milestone_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/health",
        "/api/documents",
        "/api/documents/{document_id}",
        "/api/chat",
        "/api/auth/session",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/account",
        "/api/account/password",
        "/api/account/consent",
    }


def test_allowed_local_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "access-control-allow-credentials" not in response.headers


def test_untrusted_origin_has_no_cors_permission(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers


def test_non_demo_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_mode="production")
