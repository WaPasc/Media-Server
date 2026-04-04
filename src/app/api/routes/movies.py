from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_tmdb_client
from app.schemas.movies import MovieResponse
from app.services.movie_service import get_all_movies, get_movie_by_id
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['movies'])


@router.get('/movies')
async def get_movies(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches all scanned movies and returns them with full poster URLs"""

    # Fetch all movies and their attached files
    movies = await get_all_movies(db, skip=skip, limit=limit)

    # Format response using a list comprehension
    return [MovieResponse.from_model(m, tmdb_client) for m in movies]


@router.get('/movie/{movie_id}')
async def get_movie_details(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific movie."""

    # Fetch the movie and its attached files
    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail='Movie not found')

    return MovieResponse.from_model(movie, tmdb_client)
