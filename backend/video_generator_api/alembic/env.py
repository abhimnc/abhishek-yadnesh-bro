import os
import asyncio
from logging.config import fileConfig

from dotenv import load_dotenv # Load .env file
load_dotenv() # Load environment variables from .env file

from sqlalchemy.ext.asyncio import create_async_engine # Use async engine
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# Option 1: Manually import all models and SQLModel base
# Ensure all your models are imported here so Alembic can see them
from app.db.models.base_model import SQLModelBase # Base SQLModel class
from app.db.models.user_models import User, OAuthAccount # User and OAuthAccount models
from app.db.models.payment_models import Plan # Plan model
# ... import other models as they are created

# Add naming convention for SQLAlchemy/SQLModel metadata
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# SQLModel uses a single metadata object for all its models if they don't define their own.
# If you followed standard SQLModel practice, all your models share SQLModel.metadata
from sqlmodel import SQLModel
SQLModel.metadata.naming_convention = NAMING_CONVENTION # Apply the naming convention
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired: 
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Get DATABASE_URL from environment variable (set in alembic.ini to %(DATABASE_URL)s)
# Ensure this environment variable is available when running alembic commands.
# For example, if you use a .env file, ensure it's loaded or use a wrapper like `dotenv run alembic ...`
database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Fallback to config if you prefer to set it directly in alembic.ini (not recommended for sensitive data)
    database_url = config.get_main_option("sqlalchemy.url")
if not database_url:
    raise Exception("DATABASE_URL environment variable not set and sqlalchemy.url not in alembic.ini")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here too.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include user-defined ENUM types for PostgreSQL and detect type changes
        # Make sure the schema matches your database schema if not public (e.g., for Supabase, 'public' is typical)
        # include_schemas=True, # Uncomment if you use schemas other than 'public'
        compare_type=True, # Detect type changes in columns
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True, # Detect type changes in columns
        # For multi-schema support with Alembic and SQLModel, you might need to configure include_schemas=True
        # and ensure your SQLModel tables have schema defined if not 'public'.
        # For Supabase default 'public' schema, this is usually not an issue unless explicitly using others.
        # include_schemas=True, 
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool, # NullPool is recommended for Alembic async migrations
        future=True
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online()) 