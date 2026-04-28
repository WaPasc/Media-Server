from app.core.s3 import s3_client
from app.models.media import Episode, MediaFile, Movie
from app.models.user import WatchProgress
from app.schemas.movies import MovieResponse
from app.schemas.progress import (
    ContinueWatchingEpisode,
    ContinueWatchingItem,
    ContinueWatchingMovie,
)
from app.schemas.shows import EpisodeResponse, ShowResponse
from app.services.tmdb_client import TMDBClient
from app.utils.progress import calculate_progress_percentage


def _pick_playable_file(files: list[MediaFile]) -> MediaFile | None:
    """First on-disk file, falling back to any file (so history entries for
    removed items still serialise, file_id will just be None)."""
    if not files:
        return None
    return next((f for f in files if f.is_available), None)


def build_base(progress: WatchProgress, playable: MediaFile | None) -> dict:
    duration = playable.duration if playable else None
    return dict(
        file_id=playable.id if playable else None,
        stopped_at=progress.stopped_at,
        duration=duration,
        progress_percentage=calculate_progress_percentage(
            progress.stopped_at, duration
        ),
        updated_at=progress.updated_at.isoformat(),
    )


def map_movie(
    progress: WatchProgress, movie: Movie, tmdb_client: TMDBClient
) -> ContinueWatchingMovie:
    playable = _pick_playable_file(movie.files)
    return ContinueWatchingMovie(
        **build_base(progress, playable),
        movie=MovieResponse.from_model(movie, tmdb_client),
    )


def map_episode(
    progress: WatchProgress, episode: Episode, tmdb_client: TMDBClient
) -> ContinueWatchingEpisode:
    playable = _pick_playable_file(episode.files)
    season = episode.season
    show = season.show

    return ContinueWatchingEpisode(
        **build_base(progress, playable),
        show=ShowResponse.from_model(show, tmdb_client),
        episode=EpisodeResponse(
            episode_number=episode.episode_number,
            title=episode.title,
            overview=episode.overview,
            file_id=playable.id if playable else None,
            still_url=s3_client.build_public_url(episode.still_path)
            if episode.still_path
            else None,
            still_url_fallback=tmdb_client.get_still_url(episode.still_path)
            if episode.still_path
            else None,
            library_status=episode.library_status,
        ),
        season_number=season.season_number,
    )


def map_continue_watching(
    progress: WatchProgress, tmdb_client: TMDBClient
) -> ContinueWatchingItem | None:
    if progress.movie is not None:
        return map_movie(progress, progress.movie, tmdb_client)

    if progress.episode is not None:
        return map_episode(progress, progress.episode, tmdb_client)

    return None
