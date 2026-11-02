from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["local-demo", "authenticated"] = "local-demo"
