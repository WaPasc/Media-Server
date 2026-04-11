from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.media import MediaFile, Movie
from app.services.tmdb_client import TMDBClient


async def get_all_movies(db: AsyncSession, skip: int = 0, limit: int = 50):
    stmt = (
        select(Movie)
        .options(selectinload(Movie.files).selectinload(MediaFile.progress))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_movie_by_id(db: AsyncSession, movie_id: int):
    stmt = (
        select(Movie)
        .where(Movie.id == movie_id)
        .options(selectinload(Movie.files).selectinload(MediaFile.progress))
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def refresh_movie_metadata(db: AsyncSession, tmdb: TMDBClient, movie_id: int):
    movie = await db.get(Movie, movie_id)
    if not movie or not movie.tmdb_id:
        return None

    data = await tmdb.get_movie(movie.tmdb_id)

    movie.title = data.get('title', movie.title)
    movie.overview = data.get('overview', movie.overview)
    movie.poster_path = data.get('poster_path', movie.poster_path)
    movie.backdrop_path = data.get('backdrop_path', movie.backdrop_path)

    await db.commit()
    return movie
