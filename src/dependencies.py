from fastapi import Request

from services.tmdb_client import TMDBClient


def get_tmdb_client(request: Request) -> TMDBClient:
    """Dependency to inject the TMDB client."""
    return request.app.state.tmdb_client
