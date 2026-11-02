from sqlalchemy import create_engine, text

from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.models import Chunk, Document  # noqa: F401

config = context.config
target_metadata = Base.metadata
url = Settings().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as connection:
        schema = (
            connection.scalar(text("SELECT current_schema()"))
            if connection.dialect.name == "postgresql"
            else None
        )
        # Never discover an unrelated public.alembic_version through search_path fallback.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table_schema=schema,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
