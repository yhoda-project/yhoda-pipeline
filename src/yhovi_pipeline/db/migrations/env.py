"""Alembic migration environment.

IMPORTANT: This module reads the database connection string directly from
``os.environ`` rather than instantiating ``Settings``.  This avoids the
requirement that ALL required env vars (including API keys) be present just
to run a database migration.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the shared ``Base`` so Alembic can detect schema changes.
# The models module must be imported here for its metadata to be populated.
from yhovi_pipeline.db.models import Base

# ---------------------------------------------------------------------------
# Alembic Config object (provides access to values in alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate will inspect.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Connection string resolution
# ---------------------------------------------------------------------------


def _get_url() -> str:
    """Return the database URL, reading directly from the environment.

    We intentionally bypass ``Settings`` here so that migrations can run
    with only ``DATABASE_URL`` set — no API keys needed.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. Export it before running Alembic."
        )
    return url


# ---------------------------------------------------------------------------
# Offline migration (generates SQL script without a live DB connection)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In this mode Alembic emits SQL to stdout rather than connecting to the
    database, which is useful for reviewing or applying migrations manually.
    """
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        # Render constraint names using the naming convention
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (connects to the database and applies changes)
# ---------------------------------------------------------------------------


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a live database connection."""
    # Override the sqlalchemy.url from alembic.ini with the env var value.
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
