from pydantic import BaseModel

from db_models import TVShow
from services.tmdb_client import TMDBClient


class ShowResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None

    @classmethod
    def from_models(cls, s: TVShow, tmdb_client: TMDBClient):
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
