from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_tmdb_client
from app.mappers.progress_mapper import map_continue_watching
from app.schemas.progress import (
    ContinueWatchingItem,
    ProgressResponse,
    ProgressUpdate,
    ProgressUpdateResponse,
)
from app.services.progress_service import (
    get_continue_watching,
    get_progress_for_file,
    upsert_watch_progress,
)
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['progress'])


@router.post('/progress', response_model=ProgressUpdateResponse)
async def update_progress(data: ProgressUpdate, db: AsyncSession = Depends(get_db)):
    """Receives heartbeat updates and saves watch progress."""
    user_id = 1  # TODO: Get from auth

    progress = await upsert_watch_progress(db, user_id=user_id, data=data)

    return ProgressUpdateResponse(
        status='success',
        stopped_at=progress.stopped_at,
        is_completed=progress.is_completed,
    )


@router.get('/progress/{file_id}')
async def get_progress(file_id: int, db: AsyncSession = Depends(get_db)):
    """Fetches the stopped time so the player knows where to resume."""
    progress = await get_progress_for_file(db, user_id=1, media_file_id=file_id)

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
