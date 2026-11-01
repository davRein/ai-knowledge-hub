from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Knowledge Hub API"
    app_mode: Literal["local-demo"] = "local-demo"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
