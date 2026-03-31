from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_tmdb_client
from app.mappers.progress_mapper import map_continue_watching
from app.schemas.progress import ContinueWatchingItem
from app.services.history_service import get_user_watch_history
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['history'])


@router.get('/history', response_model=list[ContinueWatchingItem])
async def get_watch_history(
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Fetches all media the user has fully completed."""
    user_id = 1  # TODO: Get from auth

    # 1. Fetch data using the new service
    progress_records = await get_user_watch_history(db, user_id)

    # 2. Map and return to the client
    return [
        item
        for p in progress_records
        if (item := map_continue_watching(p, tmdb_client))
    ]
