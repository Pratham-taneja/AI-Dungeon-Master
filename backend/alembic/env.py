"""
 Alembic migration environment.

Connects to the database using settings from config.py.
Supports both online (apply migration) and offline (generate SQL) modes.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object, provides access to values in alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Base
import world.db_models  # noqa: F401 — registers all ORM models

target_metadata = Base.metadata


def get_url() -> str:
    from config import get_settings
    settings = get_settings()
    # Alembic needs a synchronous URL
    return settings.database_sync_url


def run_migrations_offline() -> None:
    """Generate SQL scripts without connecting to the database."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Apply migrations using an async engine."""
    url = get_url()
    # Use sync driver for alembic — asyncpg not directly supported
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    from sqlalchemy import create_engine
    engine = create_engine(sync_url, poolclass=pool.NullPool)
    with engine.connect() as conn:
        do_run_migrations(conn)
    engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
