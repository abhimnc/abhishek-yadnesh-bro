import os
import asyncio
import sys
from logging.config import fileConfig

from dotenv import load_dotenv # Load .env file
load_dotenv() # Load environment variables from .env file

from sqlalchemy.ext.asyncio import create_async_engine # Use async engine
from sqlalchemy import pool
from sqlalchemy import MetaData
from sqlalchemy.sql import text # Import text construct

from alembic import context
from sqlmodel import SQLModel # Import SQLModel

# --- Define Naming Convention FIRST ---
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# --- Alembic Config ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Setup Target Metadata --- #
# Apply naming convention AFTER it's defined
SQLModel.metadata.naming_convention = NAMING_CONVENTION
target_metadata = SQLModel.metadata

# --- Get Database URL --- #
database_url = os.getenv("DATABASE_URL")
if not database_url:
    database_url = config.get_main_option("sqlalchemy.url")
if not database_url:
    raise Exception("DATABASE_URL environment variable not set and sqlalchemy.url not in alembic.ini")
config.set_main_option('sqlalchemy.url', database_url)

# --- Add project directory to sys.path --- #
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

# --- Import models AFTER sys.path modification and AFTER target_metadata is set ---
from app.db.models.base_model import SQLModelBase
from app.db.models.user_models import User, OAuthAccount, AuthProvider
from app.db.models.payment_models import Plan
from app.db.models.video_models import VideoGenerationTask, GeneratedVideo, GeneratedVideoAsset, VideoGenerationTaskStatus
from app.db.models.usage_models import UserVideoUsage

# --- Migration Functions --- #
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here too.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include user-defined Enum types for offline mode if necessary
        user_module_prefix='sqlalchemy.dialects.',
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    # Configure context to run the migrations from the script file
    context.configure(connection=connection, target_metadata=target_metadata)

    # Run the migrations
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

# --- Run Migrations --- #
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online()) 