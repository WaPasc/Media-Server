import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

POSTGRES_URL = os.getenv('POSTGRES_URL')
if not POSTGRES_URL:
    raise ValueError('POSTGRES_URL not found in environment')

SQLALCHEMY_DATABASE_URL = POSTGRES_URL.replace('postgresql://', 'postgresql+psycopg://')

# create_async_engine for async operations
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)

# SQLAlchemy 2.0 to handle async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
