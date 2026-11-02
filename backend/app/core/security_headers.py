import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("aihub.requests")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        status = 500
        path = scope.get("path", "")
        category = next(
            (
                name
                for name in ("auth", "account", "documents", "chat", "health")
                if name in path.split("/")
            ),
            "other",
        )

        async def secure_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cache-control", b"no-store"),
                        (b"x-robots-tag", b"noindex, nofollow"),
                    ]
                )
                if path.startswith("/api/"):
                    headers.append(
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
                    )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, secure_send)
        finally:
            logger.info(
                "request id=%s category=%s method=%s status=%s duration_ms=%s",
                request_id,
                category,
                scope.get("method"),
                status,
                int((time.perf_counter() - started) * 1000),
            )
