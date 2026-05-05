from pydantic import BaseModel

from app.core.s3 import s3_client
from app.models.media import TVShow
from app.schemas.credits import CastMember
from app.services.tmdb_client import TMDBClient


class ShowResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    poster_url_fallback: str | None = None
    backdrop_url: str | None = None
    backdrop_url_fallback: str | None = None
    library_status: str | None = 'present'

    @classmethod
    def from_model(cls, s: TVShow, tmdb_client: TMDBClient):
        return cls(
            id=s.id,
            title=s.title,
            year=s.year,
            overview=s.overview,
            poster_url=s3_client.build_public_url(s.poster_path)
            if s.poster_path
            else None,
            poster_url_fallback=tmdb_client.get_poster_url(s.poster_path)
            if s.poster_path
            else None,
            backdrop_url=s3_client.build_public_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            backdrop_url_fallback=tmdb_client.get_backdrop_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            library_status=s.library_status,
        )


class EpisodeResponse(BaseModel):
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


class SeasonResponse(BaseModel):
    season_number: int
    episodes: list[EpisodeResponse]
    library_status: str | None = 'present'


class ShowDetailResponse(ShowResponse):
    seasons: list[SeasonResponse]
    cast: list[CastMember] = []
    # Total cast available for this title before the slice. Lets the client
    # decide whether to render a "See all" affordance.
    total_cast_count: int = 0

    @classmethod
    def from_model(
        cls,
        s: TVShow,
        tmdb_client: TMDBClient,
        imdb_ratings: dict[str, float] | None = None,
        cast_limit: int = 50,
    ):
        # Show-level cast comes from /aggregate_credits, ordered by how many
        # episodes the actor appeared in (most prominent first), with TMDB
        # billing as the secondary tiebreaker.
        sorted_credits = sorted(
            s.credits,
            key=lambda c: (
                -(c.episode_count or 0),
                c.cast_order is None,
                c.cast_order or 0,
            ),
        )
        cast = [
            CastMember.from_credit(c, tmdb_client)
            for c in sorted_credits[:cast_limit]
        ]

        seasons_data = []

        for season in s.seasons:
            episodes_data = []
            for ep in season.episodes:
                playable = next((f for f in ep.files if f.is_available), None)
                file_id = playable.id if playable else None

                completed = next(
                    (p.is_completed for p in ep.progress if p.user_id == 1),
                    False,
                )

                rating = (
                    imdb_ratings.get(ep.imdb_id)
                    if imdb_ratings is not None and ep.imdb_id
                    else None
                )

                episodes_data.append(
                    EpisodeResponse(
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
                        imdb_rating=rating,
                    )
                )

            seasons_data.append(
                SeasonResponse(
                    season_number=season.season_number,
                    episodes=episodes_data,
                    library_status=season.library_status,
                )
            )

        return cls(
            id=s.id,
            title=s.title,
            year=s.year,
            overview=s.overview,
            poster_url=s3_client.build_public_url(s.poster_path)
            if s.poster_path
            else None,
            poster_url_fallback=tmdb_client.get_poster_url(s.poster_path)
            if s.poster_path
            else None,
            backdrop_url=s3_client.build_public_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            backdrop_url_fallback=tmdb_client.get_backdrop_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            seasons=seasons_data,
            library_status=s.library_status,
            cast=cast,
            total_cast_count=len(s.credits),
        )
