from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from services.tmdb_client import TMDBClient


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_tmdb_client(request: Request) -> TMDBClient:
    return request.app.state.tmdb_client
