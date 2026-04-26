from sqlalchemy import or_, select
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
            # Hide rows whose catalog item was removed from the library; they
            # still surface in /history.
            or_(
                WatchProgress.movie.has(Movie.library_status == 'present'),
                WatchProgress.episode.has(Episode.library_status == 'present'),
            ),
        )
        .order_by(WatchProgress.updated_at.desc())
        .limit(limit)
        .options(
            selectinload(WatchProgress.movie).options(
                selectinload(Movie.files),
                selectinload(Movie.progress),
            ),
            selectinload(WatchProgress.episode)
            .selectinload(Episode.season)
            .selectinload(Season.show),
            selectinload(WatchProgress.episode).selectinload(Episode.files),
        )
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_progress_for_file(
    db: AsyncSession, user_id: int, media_file_id: int
) -> WatchProgress | None:
    """Resolves a file_id to its catalog anchor, then looks up progress on it."""

    media_file = await db.get(MediaFile, media_file_id)
    if media_file is None:
        return None

    if media_file.movie_id is not None:
        anchor_clause = WatchProgress.movie_id == media_file.movie_id
    elif media_file.episode_id is not None:
        anchor_clause = WatchProgress.episode_id == media_file.episode_id
    else:
        return None

    stmt = select(WatchProgress).where(
        WatchProgress.user_id == user_id,
        anchor_clause,
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

        if is_finished:
            progress.has_ever_completed = True
    else:
        media_file = await db.get(MediaFile, data.file_id)
        if media_file is None or (
            media_file.movie_id is None and media_file.episode_id is None
        ):
            # Nothing to anchor to; the CHECK would reject NULL/NULL anyway.
            raise ValueError(f'media_file {data.file_id} has no catalog anchor')

        progress = WatchProgress(
            user_id=user_id,
            movie_id=media_file.movie_id,
            episode_id=media_file.episode_id,
            stopped_at=data.current_time,
            is_completed=is_finished,
            has_ever_completed=is_finished,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    return progress
