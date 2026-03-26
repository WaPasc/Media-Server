from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.media import MediaFile, Movie


async def get_all_movies(db: AsyncSession):
    stmt = select(Movie).options(
        selectinload(Movie.files).selectinload(MediaFile.progress)
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
