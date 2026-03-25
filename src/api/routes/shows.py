from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from db_models import Episode, Season, TVShow
from schemas.shows import ShowDetailResponse, ShowResponse
from services.tmdb_client import TMDBClient
from src.dependencies import get_tmdb_client

router = APIRouter(prefix='/api', tags=['shows'])


@router.get('/shows')
async def get_shows(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches all scanned TV shows and returns them with full poster URLs"""
    stmt = select(TVShow)  # Removed the invalid selectinload
    result = await db.execute(stmt)
    shows = result.scalars().all()

    return [ShowResponse.from_models(s, tmdb_client) for s in shows]


@router.get('/show/{show_id}')
async def get_show_details(
    show_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific TV show, including seasons and episodes"""

    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id)
        .options(
            selectinload(TVShow.seasons)
            .selectinload(Season.episodes)
            .selectinload(Episode.files)
        )
    )
    result = await db.execute(stmt)
    show = result.scalars().first()

    if not show:
        raise HTTPException(status_code=404, detail='TV show not found')

    return ShowDetailResponse.from_models(show, tmdb_client)
