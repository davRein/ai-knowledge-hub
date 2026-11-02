import hashlib
import hmac
import time

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import RateBucket


def consume_rate(
    session: Session, settings: Settings, category: str, identity: str, limit: int, window: int
) -> None:
    now = int(time.time())
    bucket = now // window
    key = settings.security_key.get_secret_value() if settings.security_key else "local-demo-only"
    digest = hmac.new(
        key.encode(), f"{category}:{identity}:{window}:{bucket}".encode(), hashlib.sha256
    ).hexdigest()
    insert = (
        pg_insert
        if session.bind is not None and session.bind.dialect.name == "postgresql"
        else sqlite_insert
    )
    statement = insert(RateBucket).values(key=digest, hits=1, expires_at=(bucket + 1) * window)
    counted = statement.on_conflict_do_update(
        index_elements=[RateBucket.key], set_={"hits": RateBucket.hits + 1}
    ).returning(RateBucket.hits)
    hits = session.scalar(counted)
    session.commit()
    if hits is None or hits > limit:
        retry = (bucket + 1) * window - now
        raise HTTPException(
            429,
            "Request limit reached. Please wait and try again.",
            headers={"Retry-After": str(retry)},
        )
