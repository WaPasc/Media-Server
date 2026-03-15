from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from db_models import Movie
from tmdb_client import TMDBClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tmdb_client = await TMDBClient.create(timeout=10.0)
    try:
        yield
    finally:
        await app.state.tmdb_client.close()


app = FastAPI(lifespan=lifespan)


@app.get('/api/movies')
async def get_movies(request: Request, db: AsyncSession = Depends(get_db)):
    """Fetches all scanned movies and returns them with full poster URLs"""

    # Query DB for all movies
    result = await db.execute(select(Movie))
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
        }
        for m in movies
    ]
