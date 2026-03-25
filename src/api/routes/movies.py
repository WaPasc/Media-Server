from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from db_models import Movie
from services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['movies'])


@router.get('/movies')
async def get_movies(request: Request, db: AsyncSession = Depends(get_db)):
    """Fetches all scanned movies and returns them with full poster URLs"""

    stmt = select(Movie).options(selectinload(Movie.files))
    result = await db.execute(stmt)
    movies = result.scalars().all()

    # Retrieve TMDB client from app state
    tmdb_client: TMDBClient = request.app.state.tmdb_client

    # Format response using a list comprehension
    return [
        {
            'id': m.id,
            'title': m.title,
            'year': m.year,
            'overview': m.overview,
            'poster_url': tmdb_client.get_poster_url(m.poster_path)
            if m.poster_path
            else None,
            'backdrop_url': tmdb_client.get_backdrop_url(m.backdrop_path)
            if m.backdrop_path
            else None,
            'file_id': m.files[0].id if m.files else None,
        }
        for m in movies
    ]


@router.get('/movie/{movie_id}')
async def get_movie_details(
    movie_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    """Fetches detailed info for a specific movie."""

    # Fetch the movie and its attached files
    stmt = select(Movie).where(Movie.id == movie_id).options(selectinload(Movie.files))
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail='Movie not found')

    tmdb_client: TMDBClient = request.app.state.tmdb_client

    return {
        'id': movie.id,
        'title': movie.title,
        'year': movie.year,
        'overview': movie.overview,
        'poster_url': tmdb_client.get_poster_url(movie.poster_path)
        if movie.poster_path
        else None,
        'backdrop_url': tmdb_client.get_backdrop_url(movie.backdrop_path)
        if movie.backdrop_path
        else None,
        'file_id': movie.files[0].id if movie.files else None,
    }
