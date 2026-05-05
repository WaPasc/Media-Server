from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CastLimit, get_db, get_tmdb_client
from app.schemas.episodes import EpisodeDetailResponse
from app.services.episode_service import get_episode_by_id
from app.services.imdb_dataset_service import get_ratings_for_imdb_ids
from app.services.tmdb_client import TMDBClient

router = APIRouter(prefix='/api', tags=['episodes'])


@router.get('/episode/{episode_id}')
async def get_episode_details(
    episode_id: int,
    cast_limit: CastLimit = 50,
    db: AsyncSession = Depends(get_db),
    tmdb_client: TMDBClient = Depends(get_tmdb_client),
):
    """Detail view for a single episode. Returns the episode metadata plus a
    merged cast list (show regulars + episode guest stars, deduped on person).
    """
    episode = await get_episode_by_id(db, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail='Episode not found')

    rating: float | None = None
    if episode.imdb_id:
        ratings = await get_ratings_for_imdb_ids(db, [episode.imdb_id])
        rating = ratings.get(episode.imdb_id)

    return EpisodeDetailResponse.from_model(
        episode, tmdb_client, rating, cast_limit
    )
