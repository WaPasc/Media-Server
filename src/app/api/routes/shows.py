from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CastLimit, get_db, get_tmdb_client
from app.schemas.shows import ShowDetailResponse, ShowResponse
from app.services.imdb_dataset_service import get_ratings_for_imdb_ids
from app.services.show_service import (
    get_all_shows,
    get_show_by_id,
    refresh_show_metadata,
)
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['shows'])


@router.get('/shows')
async def get_shows(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches all scanned TV shows and returns them with full poster URLs"""

    shows = await get_all_shows(db, skip=skip, limit=limit)

    return [ShowResponse.from_model(s, tmdb_client) for s in shows]


@router.get('/show/{show_id}')
async def get_show_details(
    show_id: int,
    cast_limit: CastLimit = 50,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific TV show, including seasons and episodes"""

    show = await get_show_by_id(db, show_id)

    if not show:
        raise HTTPException(status_code=404, detail='TV show not found')

    imdb_ids = [
        ep.imdb_id
        for season in show.seasons
        for ep in season.episodes
        if ep.imdb_id
    ]
    ratings = await get_ratings_for_imdb_ids(db, imdb_ids)

    return ShowDetailResponse.from_model(show, tmdb_client, ratings, cast_limit)


@router.post('/show/{show_id}/refresh')
async def refresh_show(
    show_id: int,
    db: AsyncSession = Depends(get_db),
    tmdb: TMDBClient = Depends(get_tmdb_client),
):
    updated = await refresh_show_metadata(db, tmdb, show_id)
    if not updated:
        raise HTTPException(status_code=404, detail='TV show not found')
    return {'message': 'Metadata refreshed successfully'}
