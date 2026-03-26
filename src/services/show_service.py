from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from models.media import Episode, MediaFile, Season, TVShow


async def get_all_shows(db: AsyncSession) -> list[TVShow]:
    stmt = select(TVShow)
    result = await db.execute(stmt)
    shows = result.scalars().all()

    return shows


async def get_show_by_id(db: AsyncSession, show_id: int) -> TVShow | None:
    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id)
        .options(
            selectinload(TVShow.seasons)
            .selectinload(Season.episodes)
            .selectinload(Episode.files)
            .selectinload(MediaFile.progress)
        )
    )
    result = await db.execute(stmt)
    show = result.scalars().first()

    return show
