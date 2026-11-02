"""Local operator tools. Passwords are read from the terminal, never arguments."""

import argparse
import time
from getpass import getpass

from sqlalchemy import create_engine, delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.passwords import hasher
from app.models import AuthSession, Chunk, Document, RateBucket, User
from app.schemas.auth import Registration
from app.services.auth import AuthService


def claim_demo(session: Session, settings: Settings, user: User, confirm: bool) -> int:
    """Require an explicit account and confirmation; preserve every document ID."""
    session.scalar(select(User).where(User.id == user.id).with_for_update())
    legacy = list(
        session.scalars(
            select(Document).where(
                Document.workspace_id == settings.local_workspace_id, Document.owner_id.is_(None)
            )
        )
    )
    owned = list(session.scalars(select(Document).where(Document.owner_id == user.id)))
    chunks = (
        session.scalar(
            select(func.count(Chunk.id)).where(
                Chunk.document_id.in_([doc.id for doc in legacy + owned])
            )
        )
        or 0
    )
    if (
        len(legacy) + len(owned) > settings.max_documents_per_user
        or sum(doc.size_bytes for doc in legacy + owned) > settings.max_storage_bytes_per_user
        or chunks > settings.max_chunks_per_user
    ):
        raise ValueError("Target account quota would be exceeded.")
    if confirm:
        session.execute(
            update(Document)
            .where(Document.id.in_([doc.id for doc in legacy]))
            .values(owner_id=user.id, workspace_id=user.id)
        )
        session.commit()
    else:
        session.rollback()
    return len(legacy)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["create-user", "reset-password", "claim-demo", "cleanup"]
    )
    parser.add_argument("--email")
    parser.add_argument("--confirm", action="store_true", help="Apply demo ownership transfer")
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine(settings.database_url, hide_parameters=True)
    try:
        with Session(engine, expire_on_commit=False) as session:
            if args.command == "cleanup":
                now = int(time.time())
                session.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
                session.execute(delete(RateBucket).where(RateBucket.expires_at <= now))
                session.commit()
                print("Expired sessions and rate buckets removed.")
                return
            if not args.email:
                parser.error("--email is required")
            email = args.email.strip().casefold()
            user = session.scalar(select(User).where(User.email == email))
            if args.command == "claim-demo":
                if user is None:
                    parser.error("Account does not exist. Register or create it first.")
                count = claim_demo(session, settings, user, args.confirm)
                print(
                    f"{count} legacy document(s); "
                    + (
                        "transferred."
                        if args.confirm
                        else "dry run only. Use --confirm to transfer."
                    )
                )
                return
            password = getpass("New password (12–128 characters): ")
            if password != getpass("Repeat password: "):
                parser.error("Passwords differ.")
            payload = Registration(email=email, password=password, accepted_privacy=True)
            if args.command == "create-user":
                AuthService(session, settings).register(payload)
            else:
                if user is None:
                    parser.error("Account does not exist.")
                user.password_hash = hasher.hash(password)
                AuthService(session, settings).revoke_all(user)
                session.commit()
            print("Account updated. Existing sessions revoked after password reset.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
