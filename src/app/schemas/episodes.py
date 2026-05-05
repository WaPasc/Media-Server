from pydantic import BaseModel

from app.core.s3 import s3_client
from app.models.media import Credit, Episode
from app.schemas.credits import CastMember
from app.services.tmdb_client import TMDBClient


def _merge_episode_cast(
    show_credits: list[Credit],
    episode_credits: list[Credit],
    tmdb_client: TMDBClient,
    cast_limit: int,
) -> list[CastMember]:
    """Plex/Jellyfin behavior: show regulars first (ordered by episode_count),
    then episode-specific guest stars whose person isn't already in the
    regulars list. Dedupe on person_id, the show row wins because it carries
    the more reliable character/episode_count.
    """
    show_sorted = sorted(
        show_credits,
        key=lambda c: (
            -(c.episode_count or 0),
            c.cast_order is None,
            c.cast_order or 0,
        ),
    )
    guest_sorted = sorted(
        episode_credits,
        key=lambda c: (c.cast_order is None, c.cast_order or 0),
    )

    seen: set[int] = set()
    merged: list[CastMember] = []

    for c in show_sorted:
        if len(merged) >= cast_limit:
            return merged
        if c.person.id in seen:
            continue
        seen.add(c.person.id)
        merged.append(CastMember.from_credit(c, tmdb_client))

    for c in guest_sorted:
        if len(merged) >= cast_limit:
            return merged
        if c.person.id in seen:
            continue
        seen.add(c.person.id)
        merged.append(CastMember.from_credit(c, tmdb_client))

    return merged


class EpisodeDetailResponse(BaseModel):
    id: int
    show_id: int
    season_number: int
    episode_number: int
    title: str | None = None
    overview: str | None = None
    runtime: int | None = None
    file_id: int | None = None
    still_url: str | None = None
    still_url_fallback: str | None = None
    is_completed: bool | None = False
    library_status: str | None = 'present'
    imdb_rating: float | None = None
    cast: list[CastMember] = []
    # Total deduped cast available for this episode (show regulars + episode
    # guest stars) before the slice. Lets the client decide whether to render
    # a "See all" affordance.
    total_cast_count: int = 0

    @classmethod
    def from_model(
        cls,
        ep: Episode,
        tmdb_client: TMDBClient,
        imdb_rating: float | None = None,
        cast_limit: int = 50,
    ) -> 'EpisodeDetailResponse':
        playable = next((f for f in ep.files if f.is_available), None)
        file_id = playable.id if playable else None

        completed = next(
            (p.is_completed for p in ep.progress if p.user_id == 1),
            False,
        )

        show = ep.season.show
        cast = _merge_episode_cast(
            list(show.credits), list(ep.credits), tmdb_client, cast_limit
        )
        # Deduped union of show regulars + episode guest stars on person_id,
        # matching the merge logic above. Counted here without building the
        # full CastMember list so the slice stays cheap.
        person_ids: set[int] = set()
        for c in show.credits:
            person_ids.add(c.person_id)
        for c in ep.credits:
            person_ids.add(c.person_id)
        total_cast_count = len(person_ids)

        return cls(
            id=ep.id,
            show_id=show.id,
            season_number=ep.season_number,
            episode_number=ep.episode_number,
            title=ep.title,
            overview=ep.overview,
            runtime=ep.runtime,
            file_id=file_id,
            still_url=s3_client.build_public_url(ep.still_path)
            if ep.still_path
            else None,
            still_url_fallback=tmdb_client.get_still_url(ep.still_path)
            if ep.still_path
            else None,
            is_completed=completed,
            library_status=ep.library_status,
            imdb_rating=imdb_rating,
            cast=cast,
            total_cast_count=total_cast_count,
        )
