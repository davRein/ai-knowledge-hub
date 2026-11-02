from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import Settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.upload_limit import UploadLimitMiddleware
from app.providers.base import ProviderError


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    connect_args = (
        {"connect_timeout": 5}
        if make_url(config.database_url).get_backend_name() == "postgresql"
        else {}
    )
    engine = create_engine(
        config.database_url, pool_pre_ping=True, hide_parameters=True, connect_args=connect_args
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    application = FastAPI(
        title=config.app_name,
        version="0.5.0",
        lifespan=lifespan,
        description=(
            "Milestone 5: authenticated private workspaces or explicit local demo. "
            "Publication requires the documented security/privacy review."
        ),
        docs_url="/docs" if config.app_env == "development" else None,
        redoc_url="/redoc" if config.app_env == "development" else None,
        openapi_url="/openapi.json" if config.app_env == "development" else None,
    )
    application.state.engine = engine
    application.state.settings = config
    application.add_middleware(UploadLimitMiddleware, max_bytes=config.max_upload_bytes)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=config.app_mode == "authenticated",
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.include_router(health_router)
    application.include_router(documents_router)
    application.include_router(chat_router)
    application.include_router(auth_router)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "detail": [
                    {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
            status_code=422,
        )

    @application.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            {
                "detail": "Database unavailable or schema not initialized. "
                "Check configuration and migrations."
            },
            status_code=503,
        )

    return application


app = create_app()
