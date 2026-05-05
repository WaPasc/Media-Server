import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import CursorResult, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.constants import TMDB_BACKDROP_SIZE, TMDB_POSTER_SIZE, TMDB_STILL_SIZE
from app.core.database import AsyncSessionLocal
from app.models.media import Episode, MediaFile, Movie, ScanDirectory, Season, TVShow
from app.models.user import UserShowProgress, WatchProgress  # noqa: F401
from app.services.availability_service import (
    _rollup_episode_availability,
    _rollup_movie_availability,
    _rollup_season_status,
    _rollup_show_status,
)
from app.services.credits_service import (
    sync_episode_credits,
    sync_movie_credits,
    sync_show_credits,
)
from app.services.minio_service import ensure_image_in_minio
from app.services.tmdb_client import TMDBClient
from app.utils.datetime import get_brussels_time
from app.utils.metadata import extract_local_info

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.webm'}

# How long a soft-deleted MediaFile sticks around before the daily sweep
# hard-deletes it. Long enough to survive an unmounted USB drive;
#  short enough that stale rows don't pile up forever.
GRACE_PERIOD_DAYS = 14


def _mark_unavailable(mf: 'MediaFile') -> None:
    """Flip a file to unavailable and start the grace-period clock. Callers
    are expected to gate this on the actual state change so we don't keep
    pushing deleted_at forward on every scan."""
    mf.is_available = False
    mf.deleted_at = datetime.now(timezone.utc)


def _mark_restored(mf: 'MediaFile') -> None:
    """Re-enable a file that reappeared on disk and clear the grace-period
    clock so the daily sweep won't touch it."""
    mf.is_available = True
    mf.deleted_at = None


def _normalize_title(value: str) -> str:
    return ' '.join(value.lower().strip().split())


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None

    if value is None:
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def _coerce_non_negative_int(value: Any) -> int | None:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None

    if value is None:
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed >= 0 else None


def _build_show_cache_key(title_key: str, year: int | None) -> tuple[str, int | None]:
    return (title_key, year)


async def _get_or_create_movie(
    session: AsyncSession,
    tmdb: TMDBClient,
    parsed_title: str,
    local_year: int | None,
    background_tasks: set,
) -> int | None:
    """Handles finding or creating the Movie record, including TMDB lookups."""
    search_results = await tmdb.search_movie(parsed_title)

    if not search_results.get('results'):
        logger.warning(f'No TMDB results found for: {parsed_title}')
        return None

    # Take the best match (You could also implement a loose/strict matcher here later!)
    best_match = search_results['results'][0]
    tmdb_id = best_match['id']

    # Check Database
    stmt = select(Movie).where(Movie.tmdb_id == tmdb_id)
    result = await session.execute(stmt)
    movie = result.scalars().first()

    # Create if missing
    if not movie:
        # /search/movie does not include runtime; fetch full record for it.
        full_data = await tmdb.get_movie(tmdb_id)
        parsed_year = local_year or (
            best_match.get('release_date', '')[:4]
            if best_match.get('release_date')
            else None
        )
        movie = Movie(
            tmdb_id=tmdb_id,
            title=best_match['title'],
            year=int(parsed_year) if parsed_year else None,
            overview=best_match.get('overview'),
            poster_path=best_match.get('poster_path'),
            backdrop_path=best_match.get('backdrop_path'),
            runtime=full_data.get('runtime'),
            imdb_id=full_data.get('imdb_id'),
        )
        session.add(movie)
        await session.flush()

        if movie.poster_path:
            task = asyncio.create_task(
                ensure_image_in_minio(movie.poster_path, TMDB_POSTER_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        if movie.backdrop_path:
            task = asyncio.create_task(
                ensure_image_in_minio(movie.backdrop_path, TMDB_BACKDROP_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        await sync_movie_credits(session, tmdb, movie.id, tmdb_id, background_tasks)

    return movie.id


async def process_movie_file(
    file_path: Path, session, tmdb: TMDBClient, background_tasks: set
) -> int | None:
    """Adds a new MediaFile row for a movie file. Returns the parent
    movie_id (so the caller can roll up library_status), or None if the file
    could not be matched.
    """
    abs_path = str(file_path.absolute())
    logger.info(f'Scanning new movie: {file_path.name}')

    # Extract local technical info
    local_info = await extract_local_info(Path(file_path))
    parsed_title = local_info.get('title')
    local_year = _coerce_positive_int(local_info.get('year'))

    if not parsed_title or parsed_title == 'Unknown':
        logger.warning(f'Could not parse title from filename: {file_path.name}')
        return None

    movie_id = await _get_or_create_movie(
        session, tmdb, parsed_title, local_year, background_tasks
    )
    if not movie_id:
        return None

    media_file = MediaFile(
        file_path=abs_path,
        duration=local_info.get('duration'),
        codec=local_info.get('codec'),
        resolution=local_info.get('resolution'),
        movie_id=movie_id,
    )
    session.add(media_file)
    await session.commit()
    logger.info(f'Successfully added: {parsed_title}')
    return movie_id


async def _existing_files_under(
    session: AsyncSession, abs_root: str, *, movies: bool
) -> dict[str, MediaFile]:
    """Pre-load all MediaFile rows whose file_path lives under abs_root,
    keyed by file_path. `movies=True` filters to movie files; otherwise
    episode files. autoescape=True so '_' / '%' in paths are treated literally.
    """
    prefix = abs_root + os.sep
    stmt = select(MediaFile).where(
        MediaFile.file_path.startswith(prefix, autoescape=True)
    )
    if movies:
        stmt = stmt.where(MediaFile.movie_id.is_not(None))
    else:
        stmt = stmt.where(MediaFile.episode_id.is_not(None))

    result = await session.execute(stmt)
    return {mf.file_path: mf for mf in result.scalars().all()}


async def scan_movies_directory(movies_dir: str, background_tasks: set) -> set[int]:
    """Walks a movies directory: adds new files, restores files that
    reappeared, and flips files that vanished to is_available=False.

    Returns the set of movie IDs whose file availability changed (caller
    will roll those up to library_status).
    """
    root_path = Path(movies_dir)

    if not root_path.exists() or not root_path.is_dir():
        logger.error(f'Directory not found: {movies_dir}')
        return set()

    abs_root = str(root_path.absolute())
    movies_changed: set[int] = set()

    async with TMDBClient() as tmdb:
        async with AsyncSessionLocal() as session:
            existing = await _existing_files_under(session, abs_root, movies=True)
            seen_paths: set[str] = set()

            for file_path in root_path.rglob('*'):
                if not (
                    file_path.is_file()
                    and file_path.suffix.lower() in ALLOWED_EXTENSIONS
                ):
                    continue

                abs_path = str(file_path.absolute())
                seen_paths.add(abs_path)

                known = existing.get(abs_path)
                if known is not None:
                    if not known.is_available:
                        _mark_restored(known)
                        session.add(known)
                        if known.movie_id is not None:
                            movies_changed.add(known.movie_id)
                        logger.info(f'File restored: {abs_path}')
                    continue

                try:
                    created_movie_id = await process_movie_file(
                        file_path, session, tmdb, background_tasks
                    )
                    if created_movie_id is not None:
                        movies_changed.add(created_movie_id)
                except Exception as e:
                    logger.error(f'Error processing {file_path.name}: {e}')
                    await session.rollback()

            for path, mf in existing.items():
                if path in seen_paths:
                    continue
                if mf.is_available:
                    _mark_unavailable(mf)
                    session.add(mf)
                    if mf.movie_id is not None:
                        movies_changed.add(mf.movie_id)
                    logger.warning(f'File missing: {path}')

            await session.commit()

    return movies_changed


def _find_best_tmdb_match_show(
    search_results: list[dict], title_key: str, local_year: int | None, show_title: str
) -> dict:
    """Finds the best matching TV show from TMDB search results."""
    best_match = None

    # Strict Match: Title and Year
    if local_year:
        for candidate in search_results:
            cand_name = _normalize_title(candidate.get('name', ''))
            first_air = candidate.get('first_air_date', '')
            cand_year = int(first_air[:4]) if first_air[:4].isdigit() else None

            if cand_name == title_key and cand_year == local_year:
                best_match = candidate
                break

    # Loose Match: Title Only
    if not best_match:
        for candidate in search_results:
            if _normalize_title(candidate.get('name', '')) == title_key:
                best_match = candidate
                break

    # Fallback: Trust TMDB's top result
    if not best_match:
        logger.warning(
            f"No exact match for '{show_title}'. Trusting TMDB's top result."
        )
        best_match = search_results[0]

    return best_match


async def _get_or_create_tv_show(
    session,
    tmdb: TMDBClient,
    show_title: str,
    local_year: int | None,
    cache,
    background_tasks: set,
):
    """Handles finding or creating the TVShow record, including TMDB lookups."""
    shows_by_title = cache.setdefault('shows_by_title', {})
    title_key = _normalize_title(show_title)
    show_cache_key = _build_show_cache_key(title_key, local_year)

    # Check local cache
    cached_show = shows_by_title.get(show_cache_key) or shows_by_title.get(
        _build_show_cache_key(title_key, None)
    )
    if cached_show:
        return cached_show['id'], cached_show['tmdb_id']

    # Check Database
    stmt = select(TVShow).where(func.lower(TVShow.title) == show_title.lower())
    result = await session.execute(stmt)
    tv_candidates: list[TVShow] = result.scalars().all()

    tv_show = next(
        (c for c in tv_candidates if local_year is not None and c.year == local_year),
        tv_candidates[0] if tv_candidates else None,
    )

    # Fetch from TMDB if not in DB
    if not tv_show:
        search_payload = await tmdb.search_tv_show(show_title)
        search_results = search_payload.get('results', [])

        if not search_results:
            logger.warning(f'No TMDB results found for TV show: {show_title}')
            return None, None

        best_match = _find_best_tmdb_match_show(
            search_results, title_key, local_year, show_title
        )

        show_tmdb_id = best_match['id']
        show_data = await tmdb.get_tv_show(show_tmdb_id)

        first_air_date = show_data.get('first_air_date') or best_match.get(
            'first_air_date', ''
        )
        parsed_year = (
            int(first_air_date[:4])
            if first_air_date and first_air_date[:4].isdigit()
            else local_year
        )

        tv_show = TVShow(
            tmdb_id=show_tmdb_id,
            title=show_data.get('name', show_title),
            year=parsed_year,
            overview=show_data.get('overview') or best_match.get('overview'),
            poster_path=show_data.get('poster_path') or best_match.get('poster_path'),
            backdrop_path=show_data.get('backdrop_path')
            or best_match.get('backdrop_path'),
        )
        session.add(tv_show)
        await session.flush()

        if tv_show.poster_path:
            task = asyncio.create_task(
                ensure_image_in_minio(tv_show.poster_path, TMDB_POSTER_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        if tv_show.backdrop_path:
            task = asyncio.create_task(
                ensure_image_in_minio(tv_show.backdrop_path, TMDB_BACKDROP_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        await sync_show_credits(
            session, tmdb, tv_show.id, show_tmdb_id, background_tasks
        )

    show_id = tv_show.id
    show_tmdb_id = tv_show.tmdb_id

    # Update caches
    shows_by_title[show_cache_key] = {'id': show_id, 'tmdb_id': show_tmdb_id}
    shows_by_title[_build_show_cache_key(title_key, None)] = {
        'id': show_id,
        'tmdb_id': show_tmdb_id,
    }

    return show_id, show_tmdb_id


async def _get_or_create_season(
    session,
    tmdb: TMDBClient,
    show_id,
    show_tmdb_id,
    season_number,
    cache,
    background_tasks: set,
):
    """Handles finding or creating a Season record."""
    seasons_by_key = cache.setdefault('seasons_by_key', {})
    tmdb_seasons = cache.setdefault('tmdb_seasons', {})
    season_key = (show_id, season_number)

    if season_key in seasons_by_key:
        return seasons_by_key[season_key]

    stmt = select(Season).where(
        Season.show_id == show_id, Season.season_number == season_number
    )
    result = await session.execute(stmt)
    season = result.scalars().first()

    if not season:
        tmdb_season_key = f'{show_tmdb_id}_{season_number}'
        if tmdb_season_key not in tmdb_seasons:
            tmdb_seasons[tmdb_season_key] = await tmdb.get_tv_season(
                show_tmdb_id, season_number
            )

        season_data = tmdb_seasons[tmdb_season_key]
        season = Season(
            show_id=show_id,
            tmdb_id=season_data.get('id'),
            season_number=season_number,
            title=season_data.get('name', f'Season {season_number}'),
            overview=season_data.get('overview'),
            poster_path=season_data.get('poster_path'),
        )
        session.add(season)
        await session.flush()

        if season.poster_path:
            task = asyncio.create_task(
                ensure_image_in_minio(season.poster_path, TMDB_POSTER_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

    seasons_by_key[season_key] = season.id
    return season.id


async def _get_or_create_episode(
    session,
    tmdb: TMDBClient,
    season_id,
    show_tmdb_id,
    season_number,
    episode_number,
    cache,
    background_tasks: set,
):
    """Handles finding or creating an Episode record."""
    stmt = select(Episode).where(
        Episode.season_id == season_id, Episode.episode_number == episode_number
    )
    result = await session.execute(stmt)
    episode = result.scalars().first()

    # If the episode doesn't exist, we must have TMDB data to build it
    if not episode:
        tmdb_season_key = f'{show_tmdb_id}_{season_number}'
        tmdb_seasons = cache.setdefault('tmdb_seasons', {})

        # If we skipped fetching the season earlier because it
        # already existed in the DB, we force a fetch now for the new episodes
        if tmdb_season_key not in tmdb_seasons:
            logger.info(
                f'Fetching fresh TMDB data for Show {show_tmdb_id} Season {season_number}...'
            )
            tmdb_seasons[tmdb_season_key] = await tmdb.get_tv_season(
                show_tmdb_id, season_number
            )

        season_payload = tmdb_seasons.get(tmdb_season_key, {})

        ep_data = next(
            (
                ep
                for ep in season_payload.get('episodes', [])
                if ep.get('episode_number') == episode_number
            ),
            None,
        )

        episode = Episode(
            season_id=season_id,
            tmdb_id=ep_data.get('id') if ep_data else None,
            season_number=season_number,
            episode_number=episode_number,
            title=ep_data.get('name')
            if ep_data and ep_data.get('name')
            else f'Episode {episode_number}',
            overview=ep_data.get('overview') if ep_data else None,
            still_path=ep_data.get('still_path') if ep_data else None,
            runtime=ep_data.get('runtime') if ep_data else None,
        )
        session.add(episode)
        await session.flush()

        if episode.still_path:
            task = asyncio.create_task(
                ensure_image_in_minio(episode.still_path, TMDB_STILL_SIZE)
            )
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)

        await sync_episode_credits(
            session,
            tmdb,
            episode.id,
            show_tmdb_id,
            season_number,
            episode_number,
            background_tasks,
        )

    return episode.id


async def process_tv_file(
    file_path: Path,
    session,
    tmdb: TMDBClient,
    cache: dict[str, dict[Any, Any]],
    background_tasks: set,
) -> int | None:
    """Adds a new MediaFile row for an episode file. Returns the parent
    episode_id, or None if the file could not be matched.
    """
    abs_path = str(file_path.absolute())

    # Extract metadata
    local_info = await extract_local_info(Path(abs_path))
    show_title = local_info.get('title')
    season_number = _coerce_non_negative_int(local_info.get('season'))
    episode_number = _coerce_positive_int(local_info.get('episode'))
    local_year = _coerce_positive_int(local_info.get('year'))

    if not show_title or season_number is None or episode_number is None:
        logger.warning(f'Could not parse S/E from filename: {file_path.name}')
        return None

    # Get/Create Show
    show_id, show_tmdb_id = await _get_or_create_tv_show(
        session, tmdb, show_title, local_year, cache, background_tasks
    )
    if not show_id:
        return None

    # Get/Create Season
    season_id = await _get_or_create_season(
        session, tmdb, show_id, show_tmdb_id, season_number, cache, background_tasks
    )

    # Get/Create Episode
    episode_id = await _get_or_create_episode(
        session,
        tmdb,
        season_id,
        show_tmdb_id,
        season_number,
        episode_number,
        cache,
        background_tasks,
    )

    media_file = MediaFile(
        file_path=abs_path,
        duration=local_info.get('duration'),
        codec=local_info.get('codec'),
        resolution=local_info.get('resolution'),
        episode_id=episode_id,
    )
    session.add(media_file)
    await session.commit()
    logger.info(f'Added: {show_title} - S{season_number:02d}E{episode_number:02d}')
    return episode_id


async def scan_tv_shows_directory(tv_shows_dir: str, background_tasks: set) -> set[int]:
    """Walks a TV shows directory: adds new episode files, restores files
    that reappeared, and flips files that vanished to is_available=False.

    Returns the set of episode IDs whose file availability changed.
    """
    root_path = Path(tv_shows_dir)

    if not root_path.exists() or not root_path.is_dir():
        logger.error(f'Directory not found: {tv_shows_dir}')
        return set()

    abs_root = str(root_path.absolute())
    episodes_changed: set[int] = set()

    async with TMDBClient() as tmdb:
        async with AsyncSessionLocal() as session:
            cache: dict[str, dict[Any, Any]] = {
                'shows_by_title': {},
                'seasons_by_key': {},
            }

            existing = await _existing_files_under(session, abs_root, movies=False)
            seen_paths: set[str] = set()

            for file_path in root_path.rglob('*'):
                if not (
                    file_path.is_file()
                    and file_path.suffix.lower() in ALLOWED_EXTENSIONS
                ):
                    continue

                abs_path = str(file_path.absolute())
                seen_paths.add(abs_path)

                known = existing.get(abs_path)
                if known is not None:
                    if not known.is_available:
                        _mark_restored(known)
                        session.add(known)
                        if known.episode_id is not None:
                            episodes_changed.add(known.episode_id)
                        logger.info(f'File restored: {abs_path}')
                    continue

                try:
                    created_episode_id = await process_tv_file(
                        file_path, session, tmdb, cache, background_tasks
                    )
                    if created_episode_id is not None:
                        episodes_changed.add(created_episode_id)
                except Exception as e:
                    logger.error(f'Error processing {file_path.name}: {e}')
                    await session.rollback()

            for path, mf in existing.items():
                if path in seen_paths:
                    continue
                if mf.is_available:
                    _mark_unavailable(mf)
                    session.add(mf)
                    if mf.episode_id is not None:
                        episodes_changed.add(mf.episode_id)
                    logger.warning(f'File missing: {path}')

            await session.commit()

    return episodes_changed


async def get_all_directories(session: AsyncSession):
    """Fetches all monitored directories from the database."""
    result = await session.execute(select(ScanDirectory))
    return result.scalars().all()


async def add_scan_directory(session: AsyncSession, path: str, media_type: str):
    """Adds a new directory to the database."""
    new_dir = ScanDirectory(path=path, media_type=media_type)
    session.add(new_dir)
    await session.commit()
    await session.refresh(new_dir)
    return new_dir


async def _rollup_library_status(
    movies_changed: set[int], episodes_changed: set[int]
) -> None:
    """Propagates is_available changes up the catalog hierarchy:
    Movie / Episode → Season → TVShow.
    """
    if not movies_changed and not episodes_changed:
        return

    async with AsyncSessionLocal() as session:
        await _rollup_movie_availability(session, movies_changed)
        seasons_to_check = await _rollup_episode_availability(session, episodes_changed)
        if seasons_to_check:
            await session.flush()
        shows_to_check = await _rollup_season_status(session, seasons_to_check)
        if shows_to_check:
            await session.flush()
        await _rollup_show_status(session, shows_to_check)
        await session.commit()


async def _backfill_episode_imdb_ids(session: AsyncSession, tmdb: TMDBClient) -> int:
    """Fill missing per-episode imdb_ids from TMDB so the IMDb dataset
    lookup at read time can find a rating.

    No show-level fallback: each episode has its own tconst in the IMDb
    ratings dataset, and the show's tconst would silently return the
    show's overall rating for every episode that hit the fallback. If
    TMDB has no episode-level imdb_id, leave it NULL, the episode just
    won't display a rating, which is the correct outcome.
    """
    stmt = (
        select(Episode, Season.season_number, TVShow.tmdb_id)
        .join(Season, Episode.season_id == Season.id)
        .join(TVShow, Season.show_id == TVShow.id)
        .where(Episode.imdb_id.is_(None), TVShow.tmdb_id.is_not(None))
    )
    rows = (await session.execute(stmt)).all()
    updated = 0

    for episode, season_number, show_tmdb_id in rows:
        try:
            ext = await tmdb.get_tv_episode_external_ids(
                show_tmdb_id, season_number, episode.episode_number
            )
        except Exception as e:
            logger.warning(
                'TMDB external_ids(%s, S%s E%s) failed: %s',
                show_tmdb_id,
                season_number,
                episode.episode_number,
                e,
            )
            continue

        new_id = ext.get('imdb_id')
        if new_id:
            episode.imdb_id = new_id
            updated += 1

    if updated:
        await session.commit()
    return updated


async def _backfill_imdb_ids() -> None:
    """Fill missing imdb_ids on episodes (movies already get theirs at
    create time from /movie/{id}). Cheap to run at the end of every scan
    — the SELECT short-circuits when nothing is missing.
    """
    async with TMDBClient() as tmdb, AsyncSessionLocal() as session:
        episodes_filled = await _backfill_episode_imdb_ids(session, tmdb)
        if episodes_filled:
            logger.info('IMDb id backfill: episodes=%d', episodes_filled)


async def run_full_scan():
    """Reads all directories from the DB and scans them based on their type.

    For each directory: adds new files, restores files that reappeared,
    and flips vanished files to is_available=False. After all directories
    are processed, library_status is rolled up Movie/Episode → Season → TVShow.
    """
    logger.info('Starting global background scan...')

    active_downloads: set = set()
    movies_changed: set[int] = set()
    episodes_changed: set[int] = set()

    async with AsyncSessionLocal() as session:
        stmt = select(ScanDirectory)
        result = await session.execute(stmt)
        directories = result.scalars().all()

        if not directories:
            logger.warning(
                'No directories found in database. Add one via the API first!'
            )
            return

        for directory in directories:
            logger.info(
                f'--- Scanning Directory: {directory.path} ({directory.media_type}) ---'
            )

            if directory.media_type == 'movies':
                movies_changed |= await scan_movies_directory(
                    directory.path, active_downloads
                )
            elif directory.media_type == 'shows':
                episodes_changed |= await scan_tv_shows_directory(
                    directory.path, active_downloads
                )

            directory.last_scanned = get_brussels_time()
            session.add(directory)
            await session.commit()

        if active_downloads:
            logger.info(
                f'Waiting for {len(active_downloads)} background image downloads to finish...'
            )
            await asyncio.gather(*active_downloads, return_exceptions=True)

    await _rollup_library_status(movies_changed, episodes_changed)
    await _backfill_imdb_ids()
    logger.info(
        f'--- Global Scan Complete (movies touched: {len(movies_changed)}, '
        f'episodes touched: {len(episodes_changed)}) ---'
    )


async def run_availability_scan() -> None:
    """Walks every ScanDirectory and reconciles MediaFile.is_available without
    creating new catalog rows or hitting TMDB. Files seen on disk are marked
    available, vanished files are flipped to unavailable, and library_status
    is rolled up Movie / Episode → Season → TVShow.

    Use this when you only need a fast on-disk presence sweep (e.g. after a
    drive unmount/remount); use `run_full_scan` when you also expect new
    files to ingest.
    """
    logger.info('Starting library availability scan...')

    movies_changed: set[int] = set()
    episodes_changed: set[int] = set()

    async with AsyncSessionLocal() as session:
        directories = (await session.execute(select(ScanDirectory))).scalars().all()
        if not directories:
            logger.warning(
                'No directories found in database. Add one via the API first!'
            )
            return

        for directory in directories:
            root_path = Path(directory.path)
            if not root_path.exists() or not root_path.is_dir():
                logger.error(f'Directory not found: {directory.path}')
                continue

            abs_root = str(root_path.absolute())
            is_movies = directory.media_type == 'movies'
            existing = await _existing_files_under(session, abs_root, movies=is_movies)

            seen_paths: set[str] = set()
            for file_path in root_path.rglob('*'):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in ALLOWED_EXTENSIONS
                ):
                    seen_paths.add(str(file_path.absolute()))

            for path, mf in existing.items():
                present = path in seen_paths
                if present and not mf.is_available:
                    _mark_restored(mf)
                    session.add(mf)
                    if mf.movie_id is not None:
                        movies_changed.add(mf.movie_id)
                    if mf.episode_id is not None:
                        episodes_changed.add(mf.episode_id)
                    logger.info(f'File restored: {path}')
                elif not present and mf.is_available:
                    _mark_unavailable(mf)
                    session.add(mf)
                    if mf.movie_id is not None:
                        movies_changed.add(mf.movie_id)
                    if mf.episode_id is not None:
                        episodes_changed.add(mf.episode_id)
                    logger.warning(f'File missing: {path}')

        await session.commit()

    await _rollup_library_status(movies_changed, episodes_changed)
    logger.info(
        f'--- Availability scan complete (movies touched: {len(movies_changed)}, '
        f'episodes touched: {len(episodes_changed)}) ---'
    )


async def delete_scan_directory(session: AsyncSession, directory_id: int) -> bool:
    """Removes a monitored directory from the database."""
    stmt = select(ScanDirectory).where(ScanDirectory.id == directory_id)
    result = await session.execute(stmt)
    directory = result.scalars().first()

    if not directory:
        return False  # Let the router know we couldn't find it

    await session.delete(directory)
    await session.commit()
    return True


async def cleanup_grace_expired() -> int:
    """Hard-delete MediaFile rows that have been unavailable longer than
    GRACE_PERIOD_DAYS. Returns the number of rows removed.

    Movie/Episode catalog rows are intentionally left in place: watch
    progress anchors on them, and library_status='removed' already tells
    the UI there's nothing playable. This sweep just stops orphaned file
    rows from accumulating forever.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=GRACE_PERIOD_DAYS)
    async with AsyncSessionLocal() as session:
        stmt = delete(MediaFile).where(
            MediaFile.is_available.is_(False),
            MediaFile.deleted_at.is_not(None),
            MediaFile.deleted_at < cutoff,
        )
        result = await session.execute(stmt)
        await session.commit()
        # AsyncSession.execute is typed as Result, but a DELETE returns CursorResult
        # which exposes rowcount.
        removed = max(result.rowcount, 0) if isinstance(result, CursorResult) else 0

    if removed:
        logger.info(
            'Grace-period sweep removed %d MediaFile rows older than %d days',
            removed,
            GRACE_PERIOD_DAYS,
        )
    return removed


async def run_grace_period_loop() -> None:
    """Background task: run the grace-period sweep on startup, then once
    per day. Exits cleanly on cancellation at app shutdown.

    Daily cadence is enough: a row's age is wall-clock-driven, so it
    doesn't matter whether the sweep catches it a few hours early or late.
    """
    while True:
        try:
            await cleanup_grace_expired()
        except Exception as e:
            logger.warning('Grace-period sweep failed: %s', e)
        await asyncio.sleep(86400)
