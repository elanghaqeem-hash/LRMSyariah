"""Alembic environment for the WP2 PostgreSQL governance schema."""
from __future__ import annotations
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from lrm_services.models import Base
from lrm_services import runs  # noqa: F401 - populate WP3 metadata
from lrm_services import lcr_evidence  # noqa: F401 - populate WP4/WP5 evidence metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("LRM_DATABASE_URL")
    if not url:
        raise RuntimeError("LRM_DATABASE_URL must be provided securely")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = os.getenv("LRM_DATABASE_URL")
    if not url:
        raise RuntimeError("LRM_DATABASE_URL must be provided securely")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
