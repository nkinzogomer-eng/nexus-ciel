from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy import MetaData, Table, Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if os.environ.get("NEXUS_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.environ["NEXUS_DATABASE_URL"])

metadata = MetaData()
Table(
    "runtime_snapshots",
    metadata,
    Column("snapshot_key", String(length=128), primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("timezone('utc', now())")),
)

target_metadata = metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
