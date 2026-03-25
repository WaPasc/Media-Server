from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from db_models import Episode, Season, TVShow
from services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['shows'])


@router.get('/shows')
async def get_shows(request: Request, db: AsyncSession = Depends(get_db)):
    """Fetches all scanned TV shows and returns them with full poster URLs"""
    stmt = select(TVShow)  # Removed the invalid selectinload
    result = await db.execute(stmt)
    shows = result.scalars().all()

    tmbd_client: TMDBClient = request.app.state.tmdb_client

    show_list = []
    for s in shows:
        show_list.append(
            {
                'id': s.id,
                'title': s.title,
                'year': s.year,
                'overview': s.overview,
                'poster_url': tmbd_client.get_poster_url(s.poster_path)
                if s.poster_path
                else None,
                'backdrop_url': tmbd_client.get_backdrop_url(s.backdrop_path)
                if s.backdrop_path
                else None,
            }
        )

    return show_list


@router.get('/show/{show_id}')
async def get_show_details(
    show_id: int, request: Request, db: AsyncSession = Depends(get_db)
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

    tmdb_client: TMDBClient = request.app.state.tmdb_client

    return {
        'id': show.id,
        'title': show.title,
        'year': show.year,
        'overview': show.overview,
        'poster_url': tmdb_client.get_poster_url(show.poster_path)
        if show.poster_path
        else None,
        'backdrop_url': tmdb_client.get_backdrop_url(show.backdrop_path)
        if show.backdrop_path
        else None,
        'seasons': [
            {
                'season_number': season.season_number,
                'episodes': [
                    {
                        'episode_number': ep.episode_number,
                        'title': ep.title,
                        'overview': ep.overview,
                        'file_id': ep.files[0].id if ep.files else None,
                        'still_url': tmdb_client.get_still_url(ep.still_path),
                    }
                    for ep in season.episodes
                ],
            }
            for season in show.seasons
        ],
    }
