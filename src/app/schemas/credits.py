from pydantic import BaseModel

from app.core.s3 import s3_client
from app.models.media import Credit
from app.services.credits_service import TMDB_PROFILE_SIZE
from app.services.tmdb_client import TMDBClient


class CastMember(BaseModel):
    tmdb_person_id: int
    name: str
    profile_url: str | None = None
    profile_url_fallback: str | None = None
    character: str | None = None
    cast_order: int | None = None
    # Only filled for show-level rows (from /aggregate_credits). NULL on
    # movie and episode rows.
    episode_count: int | None = None

    @classmethod
    def from_credit(cls, c: Credit, tmdb_client: TMDBClient) -> 'CastMember':
        path = c.person.profile_path
        return cls(
            tmdb_person_id=c.person.tmdb_id,
            name=c.person.name,
            profile_url=s3_client.build_public_url(path) if path else None,
            profile_url_fallback=tmdb_client.get_profile_url(path, TMDB_PROFILE_SIZE)
            if path
            else None,
            character=c.character,
            cast_order=c.cast_order,
            episode_count=c.episode_count,
        )
