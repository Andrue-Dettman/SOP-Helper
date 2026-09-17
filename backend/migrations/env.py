"""Migration credentials are separate from runtime credentials; no implicit upgrade."""
import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.database import Base

target_metadata = Base.metadata
url = os.environ.get("MIGRATION_DATABASE_URL")
if not url:
    raise RuntimeError("MIGRATION_DATABASE_URL is required for explicit migrations")


def run_migrations():
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                          dialect_opts={"paramstyle": "named"})
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()


run_migrations()
