from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from db_models import Movie
from dependencies import get_tmdb_client
from schemas.movies import MovieResponse
from services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['movies'])


@router.get('/movies')
async def get_movies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches all scanned movies and returns them with full poster URLs"""

    stmt = select(Movie).options(selectinload(Movie.files))
    result = await db.execute(stmt)
    movies = result.scalars().all()

    # Format response using a list comprehension
    return [MovieResponse.from_model(m, tmdb_client) for m in movies]


@router.get('/movie/{movie_id}')
async def get_movie_details(
    movie_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific movie."""

    # Fetch the movie and its attached files
    stmt = select(Movie).where(Movie.id == movie_id).options(selectinload(Movie.files))
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail='Movie not found')

    return MovieResponse.from_model(movie, tmdb_client)
