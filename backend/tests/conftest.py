from collections.abc import Iterator
from io import BytesIO
from os import environ
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_app


def make_pdf(texts: list[str | None], *, encrypted: bool = False) -> bytes:
    """Generate valid PDFs in memory, including image-only pages when text=None."""
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        if text is None:
            image = DecodedStreamObject()
            image.set_data(b"\x00\x00\x00")
            image.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                }
            )
            from pypdf.generic import NumberObject

            image.update(
                {
                    NameObject("/Width"): NumberObject(1),
                    NameObject("/Height"): NumberObject(1),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/XObject"): DictionaryObject(
                        {NameObject("/Im0"): writer._add_object(image)}
                    )
                }
            )
            stream = DecodedStreamObject()
            stream.set_data(b"q 100 0 0 100 0 0 cm /Im0 Do Q")
        elif text:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): writer._add_object(font)}
                    )
                }
            )
            stream = DecodedStreamObject()
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
        else:
            continue
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("test-password")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    postgres_url = environ.get("TEST_DATABASE_URL")
    if postgres_url:
        # Each test gets a unique disposable schema; no existing tables are touched.
        admin = create_engine(postgres_url, hide_parameters=True)
        schema = f"test_m2_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(sql_text(f'CREATE SCHEMA "{schema}"'))
            public_tables_before = connection.execute(
                sql_text(
                    "SELECT c.oid, c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.oid"
                )
            ).all()
        url_object = make_url(postgres_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        monkeypatch.setenv("DATABASE_URL", url_object.render_as_string(hide_password=False))
        engine = create_engine(
            url_object,
            hide_parameters=True,
            execution_options={"schema_translate_map": {None: schema}},
        )
        try:
            command.upgrade(Config("alembic.ini"), "head")
            with engine.connect() as connection:
                assert connection.scalar(sql_text("SELECT current_schema()")) == schema
                for table in (
                    "documents",
                    "chunks",
                    "users",
                    "auth_sessions",
                    "rate_buckets",
                    "alembic_version",
                ):
                    qualified = f"{schema}.{table}"
                    assert (
                        connection.scalar(
                            sql_text("SELECT to_regclass(:name)"), {"name": qualified}
                        )
                        is not None
                    )
                    assert (
                        connection.scalar(
                            sql_text(
                                "SELECT to_regclass(:name)::oid = to_regclass(:qualified)::oid"
                            ),
                            {"name": table, "qualified": qualified},
                        )
                        is True
                    )
            yield engine
        finally:
            engine.dispose()
            with admin.begin() as connection:
                connection.execute(sql_text(f'DROP SCHEMA "{schema}" CASCADE'))
                public_tables_after = connection.execute(
                    sql_text(
                        "SELECT c.oid, c.relname FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.oid"
                    )
                ).all()
                assert public_tables_after == public_tables_before, (
                    "Test changed public table identities"
                )
            admin.dispose()
        return
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: object, record: object) -> None:
        from sqlite3 import Connection

        assert isinstance(connection, Connection)
        connection.execute("PRAGMA foreign_keys=ON")

    yield engine
    engine.dispose()


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, database_url="sqlite://", max_upload_bytes=20_000)


@pytest.fixture
def document_client(engine: Engine, settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)

    def session_override() -> Iterator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client
