import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# --- NAYE IMPORTS JO HUMNE ADD KIYE HAIN ---
from app.core.config import settings
from app.db.base import Base
import app.models  # Yeh zaroori hai taaki Alembic saare models padh sake (noqa: F401 error chupanane ke liye hai)

# Alembic ka config object (.ini file padhne ke liye)
config = context.config

# Logging setup (Alembic ke console logs ke liye)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- DATABASE URL UPDATE KAREIN ---
# .env file ka URL automatically Alembic config mein set kar rahe hain
config.set_main_option("sqlalchemy.url", settings.database_url)

# --- METADATA UPDATE KAREIN ---
# Alembic ko bata rahe hain ki humari tables ka blueprint (metadata) kahan hai
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline mode: Bina database connect kiye sirf SQL queries generate/print karta hai."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Sync function jo actual migration run karta hai."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Online mode (Async): Database se connect karke actual tables create/update karta hai."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online mode start karne ka entry point."""
    asyncio.run(run_async_migrations())


# Alembic khud decide karta hai ki command offline chalayi gayi hai ya online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()