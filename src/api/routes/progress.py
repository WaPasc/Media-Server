from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies import get_db, get_tmdb_client
from mappers.progress_mapper import map_continue_watching
from models.user import WatchProgress
from schemas.progress import (
    ContinueWatchingItem,
    ProgressResponse,
    ProgressUpdate,
    ProgressUpdateResponse,
)
from services.progress_service import get_continue_watching
from services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['progress'])


@router.post('/progress')
async def update_progress(data: ProgressUpdate, db: AsyncSession = Depends(get_db)):
    """Receives heartbeat updates"""

    # Calculate if the user watched at least 90% of the video
    is_finished = False
    if data.total_duration > 0 and (data.current_time / data.total_duration) > 0.95:
        is_finished = True

    # Check if a progress row already exists for this user and file
    stmt = select(WatchProgress).where(
        WatchProgress.user_id == 1, WatchProgress.media_file_id == data.file_id
    )
    result = await db.execute(stmt)
    progress = result.scalars().first()

    if progress:
        # Update existing progress
        progress.stopped_at = data.current_time
        progress.is_completed = is_finished
    else:
        # Create new progress
        progress = WatchProgress(
            user_id=1,
            media_file_id=data.file_id,
            stopped_at=data.current_time,
            is_completed=is_finished,
        )
        db.add(progress)

    await db.commit()
    return ProgressUpdateResponse(
        status='success',
        stopped_at=progress.stopped_at,
        is_completed=progress.is_completed,
    )


@router.get('/progress/{file_id}')
async def get_progress(file_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches the stopped time so the player knows where to resume."""
    stmt = select(WatchProgress).where(
        WatchProgress.user_id == 1, WatchProgress.media_file_id == file_id
    )
    result = await db.execute(stmt)
    progress = result.scalars().first()

    if progress and not progress.is_completed:
        return ProgressResponse(stopped_at=progress.stopped_at)

    # If no progress exists, or they already finished the movie, start at 0
    return ProgressResponse(stopped_at=0.0)


@router.get('/continue-watching', response_model=list[ContinueWatchingItem])
async def continue_watching(
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    user_id = 1  # TODO: Get from auth

    progress_records = await get_continue_watching(db, user_id)

    return [
        item
        for p in progress_records
        if (item := map_continue_watching(p, tmdb_client))
    ]
