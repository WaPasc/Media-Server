from pydantic import BaseModel

from app.core.s3 import s3_client
from app.models.media import Movie
from app.services.tmdb_client import TMDBClient


class MovieResponse(BaseModel):
    id: int
    title: str
    year: int | None = None
    overview: str | None = None
    runtime: int | None = None
    poster_url: str | None = None
    poster_url_fallback: str | None = None
    backdrop_url: str | None = None
    backdrop_url_fallback: str | None = None
    file_id: int | None = None
    is_completed: bool | None = False
    library_status: str | None = 'present'
    imdb_rating: float | None = None

    @classmethod
    def from_model(
        cls,
        m: Movie,
        tmdb_client: TMDBClient,
        imdb_ratings: dict[str, float] | None = None,
    ):
        # Pick a file that's actually on disk so the player has something to
        # stream. None is fine, Qt branches on library_status for UI.
        playable = next((f for f in m.files if f.is_available), None)
        file_id = playable.id if playable else None

        completed = next(
            (p.is_completed for p in m.progress if p.user_id == 1),
            False,
        )

        rating = (
            imdb_ratings.get(m.imdb_id)
            if imdb_ratings is not None and m.imdb_id
            else None
        )

        return cls(
            id=m.id,
            title=m.title,
            year=m.year,
            overview=m.overview,
            runtime=m.runtime,
            poster_url=s3_client.build_public_url(m.poster_path)
            if m.poster_path
            else None,
            poster_url_fallback=tmdb_client.get_poster_url(m.poster_path)
            if m.poster_path
            else None,
            backdrop_url=s3_client.build_public_url(m.backdrop_path)
            if m.backdrop_path
            else None,
            backdrop_url_fallback=tmdb_client.get_backdrop_url(m.backdrop_path)
            if m.backdrop_path
            else None,
            file_id=file_id,
            is_completed=completed,
            library_status=m.library_status,
            imdb_rating=rating,
        )
