"""
Alembic Environment Configuration
==================================

This env.py:
  - Reads DATABASE_URL from the .env file via app.core.config.settings
  - Imports all SQLAlchemy models so Alembic sees them for autogenerate
  - Supports both online (connected) and offline (SQL script) migration modes
"""

from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Make the app package importable from the backend/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings  # noqa: E402
from app.database.base import Base    # noqa: E402

# Import all models so their tables are registered in Base.metadata
import app.models.project       # noqa: F401, E402
import app.models.climate       # noqa: F401, E402
import app.models.shelter       # noqa: F401, E402
import app.models.material      # noqa: F401, E402
import app.models.simulation    # noqa: F401, E402
import app.models.optimization  # noqa: F401, E402

# ──────────────────────────────────────────────────────────────────────────────
# Alembic Config object (gives access to alembic.ini values)
# ──────────────────────────────────────────────────────────────────────────────

config = context.config

# Override sqlalchemy.url with the value from .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Migration modes
# ──────────────────────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
