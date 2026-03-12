import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv 

load_dotenv() # This loads variables from .env into os.environ 

POSTGRES_URL = os.getenv("POSTGRES_URL")
ASYNC_URL = POSTGRES_URL.replace("postgresql://","postgresql+psycopg://")

async_engine = create_async_engine(
    ASYNC_URL
)