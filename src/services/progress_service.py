from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db_models import Episode, MediaFile, Movie, Season, WatchProgress


async def get_continue_watching(db, user_id: int, limit: int = 10):
    stmt = (
        select(WatchProgress)
        .where(
            WatchProgress.user_id == user_id,
            ~WatchProgress.is_completed,
            WatchProgress.stopped_at > 0,
        )
        .order_by(WatchProgress.updated_at.desc())
        .limit(limit)
        .options(
            selectinload(WatchProgress.media_file)
            .selectinload(MediaFile.movie)
            .selectinload(Movie.files),
            selectinload(WatchProgress.media_file)
            .selectinload(MediaFile.episode)
            .selectinload(Episode.season)
            .selectinload(Season.show),
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()
