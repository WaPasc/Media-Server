from pydantic import BaseModel

from app.models.media import TVShow
from app.services.tmdb_client import TMDBClient


class ShowResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    is_available: bool | None = True

    @classmethod
    def from_model(cls, s: TVShow, tmdb_client: TMDBClient):
        return cls(
            id=s.id,
            title=s.title,
            year=s.year,
            overview=s.overview,
            poster_url=tmdb_client.get_poster_url(s.poster_path)
            if s.poster_path
            else None,
            backdrop_url=tmdb_client.get_backdrop_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            is_available=s.is_available,
        )


class EpisodeResponse(BaseModel):
    episode_number: int
    title: str
    overview: str | None = None
    file_id: int | None = None
    still_url: str | None = None
    is_completed: bool | None = False
    is_available: bool | None = True


class SeasonResponse(BaseModel):
    season_number: int
    episodes: list[EpisodeResponse]


class ShowDetailResponse(ShowResponse):
    seasons: list[SeasonResponse]

    @classmethod
    def from_model(cls, s: TVShow, tmdb_client: TMDBClient):
        seasons_data = []

        for season in s.seasons:
            episodes_data = []
            for ep in season.episodes:
                # extract completion status
                completed = False
                file_id = None
                if ep.files:
                    # Pick a valid file for the video player
                    preferred_file = next(
                        (f for f in ep.files if f.is_available), ep.files[0]
                    )
                    if preferred_file.is_available:
                        file_id = preferred_file.id

                    if preferred_file.progress:
                        completed = next(
                            (
                                p.is_completed
                                for p in preferred_file.progress
                                if p.user_id == 1
                            ),
                            False,
                        )

                episodes_data.append(
                    EpisodeResponse(
                        episode_number=ep.episode_number,
                        title=ep.title,
                        overview=ep.overview,
                        file_id=file_id,
                        still_url=tmdb_client.get_still_url(ep.still_path)
                        if ep.still_path
                        else None,
                        is_completed=completed,
                        is_available=ep.is_available,
                    )
                )

            seasons_data.append(
                SeasonResponse(
                    season_number=season.season_number, episodes=episodes_data
                )
            )

        return cls(
            id=s.id,
            title=s.title,
            year=s.year,
            overview=s.overview,
            poster_url=tmdb_client.get_poster_url(s.poster_path)
            if s.poster_path
            else None,
            backdrop_url=tmdb_client.get_backdrop_url(s.backdrop_path)
            if s.backdrop_path
            else None,
            seasons=seasons_data,
            is_available=s.is_available,
        )
