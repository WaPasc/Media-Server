from db_models import WatchProgress
from schemas.movies import MovieResponse
from schemas.progress import (
    ContinueWatchingEpisode,
    ContinueWatchingItem,
    ContinueWatchingMovie,
)
from schemas.shows import EpisodeResponse, ShowResponse
from services.tmdb_client import TMDBClient
from utils.progress import calculate_progress_percentage


def build_base(progress: WatchProgress) -> dict:
    media = progress.media_file

    return dict(
        file_id=media.id,
        stopped_at=progress.stopped_at,
        duration=media.duration,
        progress_percentage=calculate_progress_percentage(progress),
        updated_at=progress.updated_at.isoformat(),
    )


def map_movie(
    progress: WatchProgress, tmdb_client: TMDBClient
) -> ContinueWatchingMovie:
    media = progress.media_file

    return ContinueWatchingMovie(
        **build_base(progress),
        movie=MovieResponse.from_model(media.movie, tmdb_client),
    )


def map_episode(
    progress: WatchProgress, tmdb_client: TMDBClient
) -> ContinueWatchingEpisode:
    media = progress.media_file
    episode = media.episode
    season = episode.season
    show = season.show

    return ContinueWatchingEpisode(
        **build_base(progress),
        show=ShowResponse.from_model(show, tmdb_client),
        episode=EpisodeResponse(
            episode_number=episode.episode_number,
            title=episode.title,
            overview=episode.overview,
            file_id=media.id,
            still_url=tmdb_client.get_still_url(episode.still_path)
            if episode.still_path
            else None,
        ),
        season_number=season.season_number,
    )


def map_continue_watching(
    progress: WatchProgress, tmdb_client: TMDBClient
) -> ContinueWatchingItem | None:
    media = progress.media_file

    if not media:
        return None

    if media.movie:
        return map_movie(progress, tmdb_client)

    if media.episode:
        return map_episode(progress, tmdb_client)

    return None
