from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_tmdb_client
from app.schemas.movies import MovieResponse
from app.services.imdb_dataset_service import get_ratings_for_imdb_ids
from app.services.movie_service import (
    get_all_movies,
    get_movie_by_id,
    refresh_movie_metadata,
)
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

    movies = await get_all_movies(db, skip=skip, limit=limit)

    imdb_ids = [m.imdb_id for m in movies if m.imdb_id]
    ratings = await get_ratings_for_imdb_ids(db, imdb_ids)

    return [MovieResponse.from_model(m, tmdb_client, ratings) for m in movies]


@router.get('/movie/{movie_id}')
async def get_movie_details(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches detailed info for a specific movie."""

    movie = await get_movie_by_id(db, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail='Movie not found')

    ratings = (
        await get_ratings_for_imdb_ids(db, [movie.imdb_id]) if movie.imdb_id else {}
    )

    return MovieResponse.from_model(movie, tmdb_client, ratings)


@router.post('/movies/{movie_id}/refresh')
async def refresh_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    tmdb: TMDBClient = Depends(get_tmdb_client),
):
    updated = await refresh_movie_metadata(db, tmdb, movie_id)
    if not updated:
        raise HTTPException(status_code=404, detail='Movie not found')
    return {'message': 'Metadata refreshed successfully'}
