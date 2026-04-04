from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_tmdb_client
from app.schemas.shows import ShowDetailResponse, ShowResponse
from app.services.show_service import get_all_shows, get_show_by_id
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
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific TV show, including seasons and episodes"""

    show = await get_show_by_id(db, show_id)

    if not show:
        raise HTTPException(status_code=404, detail='TV show not found')

    return ShowDetailResponse.from_model(show, tmdb_client)
