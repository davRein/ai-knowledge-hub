"""Explicit local-demo reindex: python -m app.reindex (never runs on startup)."""

import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User
from app.providers.factory import create_provider
from app.services.embeddings import reindex_workspace


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicitly reindex one workspace.")
    parser.add_argument("--email", help="Required in authenticated mode")
    args = parser.parse_args()
    settings = Settings()
    provider = create_provider(settings)
    engine = create_engine(settings.database_url, hide_parameters=True)
    try:
        with Session(engine) as session:
            owner_id = None
            workspace_id = settings.local_workspace_id
            if settings.app_mode == "authenticated":
                if not args.email:
                    parser.error("Authenticated reindex requires --email.")
                user = session.scalar(select(User).where(User.email == args.email.casefold()))
                if user is None:
                    parser.error("Account does not exist.")
                if settings.ai_provider == "openai" and not user.external_ai_consent:
                    parser.error("Account must consent to external AI in the UI first.")
                owner_id = workspace_id = user.id
            succeeded, failed = reindex_workspace(session, workspace_id, provider, owner_id)
            print(f"Provider: {provider.name}; indexed: {succeeded}; failed: {failed}")
            if failed:
                raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
