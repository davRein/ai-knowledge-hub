from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    app_name: str = "AI Knowledge Hub API"
    app_mode: Literal["local-demo", "authenticated"] = "local-demo"
    app_env: Literal["development", "production"] = "development"
    security_key: SecretStr | None = None
    allow_registration: bool = False
    auth_cookie_secure: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    login_ip_per_minute: int = Field(default=20, ge=1)
    login_account_per_15min: int = Field(default=10, ge=1)
    requests_per_minute: int = Field(default=120, ge=1)
    chat_per_minute: int = Field(default=20, ge=1)
    uploads_per_hour: int = Field(default=30, ge=1)
    max_documents_per_user: int = Field(default=50, ge=1)
    max_storage_bytes_per_user: int = Field(default=209715200, ge=1)
    max_chunks_per_user: int = Field(default=10000, ge=1)
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    database_url: str = Field(
        default="postgresql+psycopg://knowledge_hub:local_demo_only_change_me@127.0.0.1:5432/knowledge_hub",
        repr=False,
    )
    local_workspace_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    max_pdf_pages: int = Field(default=500, ge=1, le=5000)
    max_extracted_chars: int = Field(default=2_000_000, ge=1)
    ai_provider: Literal["fake", "openai"] = "fake"
    openai_api_key: SecretStr | None = None
    openai_embedding_model: Literal["text-embedding-3-small", "text-embedding-3-large"] = (
        "text-embedding-3-small"
    )
    openai_answer_model: str = "gpt-4.1-mini"
    retrieval_top_k: int = Field(default=5, ge=1, le=10)
    retrieval_min_similarity: float = Field(default=0.25, ge=0, le=1)

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.app_mode == "authenticated" and (
            not self.security_key or len(self.security_key.get_secret_value()) < 32
        ):
            raise ValueError("Authenticated mode requires a SECURITY_KEY of at least 32 characters")
        for origin in self.cors_origins:
            url = urlsplit(origin)
            if (
                url.scheme not in {"http", "https"}
                or not url.netloc
                or url.path
                or url.query
                or url.fragment
                or "*" in origin
                or url.username
            ):
                raise ValueError(
                    "CORS_ORIGINS must contain exact HTTP(S) origins without paths or wildcards"
                )
        if self.app_env == "production":
            if (
                self.app_mode != "authenticated"
                or not self.auth_cookie_secure
                or self.allow_registration
            ):
                raise ValueError(
                    "Production requires authenticated mode, secure cookies and closed registration"
                )
            if not self.cors_origins or any(
                not origin.startswith("https://") for origin in self.cors_origins
            ):
                raise ValueError("Production requires explicit HTTPS frontend origins")
            if not self.allowed_hosts or any(
                host in {"*", "localhost", "127.0.0.1", "testserver"} for host in self.allowed_hosts
            ):
                raise ValueError("Production requires explicit public ALLOWED_HOSTS")
            if "local_demo_only_change_me" in self.database_url:
                raise ValueError("Production must not use the example database credential")
        return self
