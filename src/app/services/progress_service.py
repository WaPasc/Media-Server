from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaFile, Movie, Season
from app.models.user import WatchProgress
from app.schemas.progress import ProgressUpdate
from app.utils.progress import check_is_completed


async def get_continue_watching(
    db: AsyncSession, user_id: int, limit: int = 10
) -> list[WatchProgress]:
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
            .selectinload(Movie.files)
            .selectinload(MediaFile.progress),
            selectinload(WatchProgress.media_file)
            .selectinload(MediaFile.episode)
            .selectinload(Episode.season)
            .selectinload(Season.show),
        )
    )

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_progress_for_file(
    db: AsyncSession, user_id: int, media_file_id: int
) -> WatchProgress | None:
    stmt = select(WatchProgress).where(
        WatchProgress.user_id == user_id,
        WatchProgress.media_file_id == media_file_id,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def upsert_watch_progress(
    db: AsyncSession, user_id: int, data: ProgressUpdate
) -> WatchProgress:
    """Updates existing progress or creates a new record if none exists."""

    is_finished = check_is_completed(data.current_time, data.total_duration)
    progress = await get_progress_for_file(db, user_id, data.file_id)

    if progress:
        progress.stopped_at = data.current_time
        progress.is_completed = is_finished
    else:
        progress = WatchProgress(
            user_id=user_id,
            media_file_id=data.file_id,
            stopped_at=data.current_time,
            is_completed=is_finished,
        )
        db.add(progress)

    await db.commit()

    # Refresh the object after a commit if returning it
    await db.refresh(progress)

    return progress
