from typing import Annotated, AsyncGenerator

from fastapi import Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.tmdb_client import TMDBClient


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_tmdb_client(request: Request) -> TMDBClient:
    return request.app.state.tmdb_client


# Shared query parameter for the cast slice on movie/show/episode detail
# endpoints. Default 50 keeps the desktop strip light; le=5000 covers even
# long-running TMDB shows when the user opens "See all".
CastLimit = Annotated[
    int,
    Query(
        ge=1,
        le=5000,
        description=(
            'Max cast entries to return. Default 50, raise up to 5000 to '
            'fetch the full list (used by "See all" views).'
        ),
    ),
]
