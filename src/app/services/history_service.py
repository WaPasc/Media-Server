from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaFile, Movie, Season
from app.models.user import WatchProgress


async def get_user_watch_history(db: AsyncSession, user_id: int) -> list[WatchProgress]:
    """Fetches all media the user has fully completed, ordered by most recently watched."""

    stmt = (
        select(WatchProgress)
        .where(
            WatchProgress.user_id == user_id,
            WatchProgress.has_ever_completed,
        )
        .order_by(desc(WatchProgress.updated_at))
        .options(
            selectinload(WatchProgress.media_file)
            .selectinload(MediaFile.movie)
            .selectinload(Movie.files)
            .selectinload(MediaFile.progress),
            selectinload(WatchProgress.media_file)
            .selectinload(MediaFile.episode)
            .selectinload(Episode.season)
            .selectinload(Season.show),
        )
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
