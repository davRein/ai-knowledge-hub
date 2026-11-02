from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadLimitMiddleware:
    """Bound multipart bytes before Starlette parses/spools the upload."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes + 64 * 1024  # Multipart boundary/header allowance.

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] not in {"POST", "PATCH", "DELETE"}
            or not (
                scope["path"].rstrip("/") in {"/api/documents", "/api/chat", "/api/account"}
                or scope["path"].startswith(("/api/auth/", "/api/account/"))
            )
        ):
            await self.app(scope, receive, send)
            return
        body = bytearray()
        max_bytes = (
            self.max_bytes
            if scope["path"].rstrip("/") == "/api/documents" and scope["method"] == "POST"
            else 16 * 1024
        )
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            part = message.get("body", b"")
            if len(body) + len(part) > max_bytes:
                response = JSONResponse({"detail": "Upload request exceeds the size limit."}, 413)
                await response(scope, receive, send)
                return
            body.extend(part)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
