"""Explicit demo seeding: python -m app.ingestion --corpus data/sops.

Requires WAREHOUSE_SEED_DATABASE_URL for a local demo database and an already
migrated schema. Never runs on API startup. Never prints database credentials.
"""

import argparse
import asyncio
import os
from pathlib import Path
import selectors
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .catalog import Generation
from .models import SourceValidationError, stable_id
from .postgres import ingest_postgres


def validate_demo_url(value):
    url = make_url(value)
    if (url.drivername != 'postgresql+psycopg' or url.host not in ('localhost', '127.0.0.1', 'db')
            or not url.database or not (url.database == 'warehouse' or url.database.startswith('warehouse_'))):
        raise SourceValidationError('Seeding requires an explicitly configured local warehouse demo database')
    return url


async def seed(args):
    value = os.environ.get('WAREHOUSE_SEED_DATABASE_URL')
    if not value:
        raise SourceValidationError('WAREHOUSE_SEED_DATABASE_URL is required')
    url = validate_demo_url(value)
    generation, provider = None, None
    if args.mode == 'embedding':
        from app.providers.openai import OpenAIEmbeddingProvider
        model, key = os.environ.get('OPENAI_EMBEDDING_MODEL'), os.environ.get('OPENAI_API_KEY')
        if not model or not key or args.dimension is None:
            raise SourceValidationError('Embedding mode requires model, key, and explicit --dimension')
        generation = Generation(stable_id('openai', model, str(args.dimension)), 'openai', model, args.dimension)
        provider = OpenAIEmbeddingProvider(key, model, dimension=args.dimension)
    engine = create_async_engine(url, connect_args={'connect_timeout': 10})
    try:
        async with asyncio.timeout(120):
            revision = await ingest_postgres(args.corpus, async_sessionmaker(engine, expire_on_commit=False),
                                             generation=generation, provider=provider)
        print(f'Published fictional corpus revision {revision} ({args.mode}).')
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--mode', choices=('lexical', 'embedding'), default='lexical')
    parser.add_argument('--dimension', type=int)
    args = parser.parse_args()
    try:
        if sys.platform == 'win32':
            asyncio.run(seed(args), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
        else:
            asyncio.run(seed(args))
    except SourceValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('Corpus indexing failed; the active revision was not replaced. Check demo database/provider configuration.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
