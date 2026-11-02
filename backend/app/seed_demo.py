"""Explicit, repeatable import of the bundled CC0 PDF; never runs on startup."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Chunk, User
from app.providers.fake import FakeProvider
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
from app.services.pdf import extract_pdf

SAMPLE_PDF = Path(__file__).resolve().parents[2] / "examples/atlas-handbook.pdf"
# Editable monorepo installation: backend/app/ -> backend/ -> repository root.


@dataclass(frozen=True)
class SeedResult:
    status: Literal["preview", "created", "existing"]
    document_id: UUID | None = None


def seed_sample(
    session: Session, settings: Settings, email: str | None = None, *, confirm: bool = False
) -> SeedResult:
    if settings.app_env != "development" or settings.ai_provider != "fake":
        raise ValueError("Sample seeding requires development mode and AI_PROVIDER=fake.")
    workspace_id, owner_id = settings.local_workspace_id, None
    if settings.app_mode == "authenticated":
        if not email:
            raise ValueError("Select an existing account with --email; no account is created.")
        user = session.scalar(select(User).where(User.email == email.strip().casefold()))
        if user is None:
            raise ValueError("Account does not exist. Register in the UI first.")
        workspace_id = owner_id = user.id
    elif email:
        raise ValueError("--email is only valid in authenticated mode.")
    data = SAMPLE_PDF.read_bytes()
    expected = extract_pdf(data, settings)
    repository = DocumentRepository(session, workspace_id, owner_id, settings)
    matches = [doc for doc in repository.list_documents() if doc.filename == SAMPLE_PDF.name]
    if len(matches) > 1:
        raise ValueError("Multiple sample filenames exist. Resolve them explicitly before seeding.")
    if matches:
        document = matches[0]
        chunks = list(
            session.scalars(
                select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index)
            )
        )
        if (
            document.status != "ready"
            or document.embedding_status != "ready"
            or [(chunk.page_number, chunk.content) for chunk in chunks] != expected.chunks
            or any(
                chunk.embedding is None or chunk.embedding_model != FakeProvider.profile
                for chunk in chunks
            )
        ):
            raise ValueError(
                "An incompatible sample filename already exists. "
                "Rename/delete it in the UI or explicitly reindex; nothing was changed."
            )
        return SeedResult("existing", document.id)
    if not confirm:
        return SeedResult("preview")
    document = DocumentService(repository, settings, FakeProvider()).ingest(
        data, SAMPLE_PDF.name, "application/pdf"
    )
    if document.status != "ready" or document.embedding_status != "ready":
        raise ValueError(
            "Sample ingestion failed. Inspect its status in Documents before retrying."
        )
    return SeedResult("created", document.id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="Required for authenticated workspaces")
    parser.add_argument("--confirm", action="store_true", help="Apply import; default is read-only")
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine(settings.database_url, hide_parameters=True)
    try:
        with Session(engine, expire_on_commit=False) as session:
            try:
                result = seed_sample(session, settings, args.email, confirm=args.confirm)
            except ValueError as exc:
                parser.exit(1, f"{exc}\n")
            print(f"Sample: {result.status}; document ID: {result.document_id or 'none'}.")
            if result.status == "preview":
                print("No changes made. Add --confirm to import into this selected workspace.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
