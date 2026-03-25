from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from db_models import WatchProgress
from schemas.progress import ProgressUpdate

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
    return {
        'status': 'success',
        'stopped_at': progress.stopped_at,
        'is_completed': progress.is_completed,
    }


@router.get('/progress/{file_id}')
async def get_progress(file_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches the stopped time so the player knows where to resume."""
    stmt = select(WatchProgress).where(
        WatchProgress.user_id == 1, WatchProgress.media_file_id == file_id
    )
    result = await db.execute(stmt)
    progress = result.scalars().first()

    if progress and not progress.is_completed:
        return {'stopped_at': progress.stopped_at}

    # If no progress exists, or they already finished the movie, start at 0
    return {'stopped_at': 0.0}
