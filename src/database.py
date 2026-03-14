import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

POSTGRES_URL = os.getenv('POSTGRES_URL')
ASYNC_URL = POSTGRES_URL.replace('postgresql://', 'postgresql+psycopg://')

if not ASYNC_URL:
    raise ValueError('The database URL is not working')

# create_async_engine for async operations
engine = create_async_engine(ASYNC_URL, echo=False)

# SQLAlchemy 2.0 to handle async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    """Dependency for FastAPI to get a database session."""
    async with AsyncSessionLocal() as session:
        yield session
