from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel # Ensure SQLModel is imported if models will be created here or for metadata

from app.core.config import settings

# Create the async engine
# For production, you might want to adjust pool settings, etc.
async_engine = create_async_engine(
    str(settings.DATABASE_URL), # pydantic V2 returns a Dsn object, ensure it's a string
    echo=True, # Log SQL queries, set to False in production
    future=True, # Use the new style of engine
    pool_size=5,  # Example pool size
    max_overflow=10, # Example max overflow
    pool_timeout=30, # Example timeout waiting for connection
    pool_recycle=1800 # Recycle connections older than 30 minutes (important!)
)

# Create a sessionmaker for generating AsyncSession instances
# expire_on_commit=False is important for FastAPI background tasks or if you pass objects outside the session scope
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_async_session() -> AsyncSession:
    """Dependency to get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit if all operations in the request were successful
        except Exception:
            await session.rollback() # Rollback on any exception
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize the database. 
    In a production environment, you would use Alembic migrations.
    This function can be useful for development and testing with a clean DB.
    """
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Uncomment to drop all tables first
        await conn.run_sync(SQLModel.metadata.create_all) 