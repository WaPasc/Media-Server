from pydantic import BaseModel

from models.media import Movie
from services.tmdb_client import TMDBClient


class MovieResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    file_id: int | None = None

    @classmethod
    def from_model(cls, m: Movie, tmdb_client: TMDBClient):
        return cls(
            id=m.id,
            title=m.title,
            year=m.year,
            overview=m.overview,
            poster_url=tmdb_client.get_poster_url(m.poster_path)
            if m.poster_path
            else None,
            backdrop_url=tmdb_client.get_backdrop_url(m.backdrop_path)
            if m.backdrop_path
            else None,
            file_id=m.files[0].id if m.files else None,
        )
