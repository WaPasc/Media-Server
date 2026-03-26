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
    is_completed: bool | None = False

    @classmethod
    def from_model(cls, m: Movie, tmdb_client: TMDBClient):
        completed = False
        if m.files and m.files[0].progress:
            # Hardcoded MVP user_id=1: prefer that record if present.
            user_progress = next(
                (p for p in m.files[0].progress if p.user_id == 1),
                m.files[0].progress[0],
            )
            completed = user_progress.is_completed
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
            is_completed=completed,
        )
