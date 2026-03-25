from pydantic import BaseModel

from models.media import TVShow
from services.tmdb_client import TMDBClient


class ShowResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None

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
        )


class EpisodeResponse(BaseModel):
    episode_number: int
    title: str
    overview: str | None = None
    file_id: int | None = None
    still_url: str | None = None


class SeasonResponse(BaseModel):
    season_number: int
    episodes: list[EpisodeResponse]


class ShowDetailResponse(ShowResponse):
    seasons: list[SeasonResponse]

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
            seasons=[
                SeasonResponse(
                    season_number=season.season_number,
                    episodes=[
                        EpisodeResponse(
                            episode_number=ep.episode_number,
                            title=ep.title,
                            overview=ep.overview,
                            file_id=ep.files[0].id if ep.files else None,
                            still_url=tmdb_client.get_still_url(ep.still_path)
                            if ep.still_path
                            else None,
                        )
                        for ep in season.episodes
                    ],
                )
                for season in s.seasons
            ],
        )
