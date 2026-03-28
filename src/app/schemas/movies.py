from pydantic import BaseModel

from app.models.media import Movie
from app.services.tmdb_client import TMDBClient


class MovieResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    file_id: int | None = None
    is_completed: bool | None = False
    is_available: bool | None = True

    @classmethod
    def from_model(cls, m: Movie, tmdb_client: TMDBClient):
        completed = False
        file_id = None
        if m.files:
            # pick a valid file to send to the video player
            preferred_file = next((f for f in m.files if f.is_available), m.files[0])
            if preferred_file.is_available:
                file_id = preferred_file.id

            if preferred_file.progress:
                user_progress = next(
                    (p for p in preferred_file.progress if p.user_id == 1),
                    preferred_file.progress[0],
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
            file_id=file_id,
            is_completed=completed,
            is_available=m.is_available,
        )
