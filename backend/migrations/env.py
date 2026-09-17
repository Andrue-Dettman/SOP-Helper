"""Migration credentials are separate from runtime credentials; no implicit upgrade."""
import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.api.migration_support import collect_metadata, revision_guard

target_metadata, missing_domains = collect_metadata()
url = os.environ.get("MIGRATION_DATABASE_URL")
if not url:
    raise RuntimeError("MIGRATION_DATABASE_URL is required for explicit migrations")


def run_migrations():
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                          dialect_opts={"paramstyle": "named"},
                          process_revision_directives=revision_guard(missing_domains))
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata,
                              process_revision_directives=revision_guard(missing_domains))
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()


run_migrations()
