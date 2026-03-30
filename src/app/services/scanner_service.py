import asyncio
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.metadata import extract_local_info
from app.models.media import Episode, MediaFile, Movie, ScanDirectory, Season, TVShow
from app.models.user import UserShowProgress, WatchProgress  # noqa: F401
from app.services.tmdb_client import TMDBClient
from app.utils.datetime import get_brussels_time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.webm'}


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


async def process_movie_file(file_path: Path, session, tmdb: TMDBClient):
    """Processes a single movie file, fetches TMDB data, and saves to DB."""
    abs_path = str(file_path.absolute())

    # Skip if already in database
    stmt = select(MediaFile).where(MediaFile.file_path == abs_path)
    result = await session.execute(stmt)
    if result.scalars().first():
        logger.info(f'Skipping (already scanned): {file_path.name}')
        return

    logger.info(f'Scanning new movie: {file_path.name}')

    # Extract local technical info (run in thread to prevent blocking async loop)
    local_info = await asyncio.to_thread(extract_local_info, abs_path)
    parsed_title = local_info.get('title')

    if not parsed_title or parsed_title == 'Unknown':
        logger.warning(f'Could not parse title from filename: {file_path.name}')
        return

    # Search TMDB
    search_results = await tmdb.search_movie(parsed_title)

    if not search_results.get('results'):
        logger.warning(f'No TMDB results found for: {parsed_title}')
        return

    # Take the best match
    best_match = search_results['results'][0]
    tmdb_id = best_match['id']

    # Check if we already have this Movie's metadata in the DB
    stmt = select(Movie).where(Movie.tmdb_id == tmdb_id)
    result = await session.execute(stmt)
    movie = result.scalars().first()

    # If not, create the Movie metadata record
    if not movie:
        parsed_year = local_info.get('year') or (
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
        )
        session.add(movie)
        await session.flush()  # Generates the movie.id without fully committing

    # Link the physical MediaFile to the Movie
    media_file = MediaFile(
        file_path=abs_path,
        duration=local_info.get('duration'),
        codec=local_info.get('codec'),
        resolution=local_info.get('resolution'),
        movie_id=movie.id,
    )
    session.add(media_file)
    await session.commit()
    logger.info(f'Successfully added: {movie.title}')


async def scan_movies_directory(movies_dir: str):
    """Walks the movie directory and orchestrates the scanning."""
    root_path = Path(movies_dir)

    if not root_path.exists() or not root_path.is_dir():
        logger.error(f'Directory not found: {movies_dir}')
        return

    # Use the async context managers we built!
    async with TMDBClient() as tmdb:
        async with AsyncSessionLocal() as session:
            for file_path in root_path.rglob('*'):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in ALLOWED_EXTENSIONS
                ):
                    try:
                        await process_movie_file(file_path, session, tmdb)
                    except Exception as e:
                        logger.error(f'Error processing {file_path.name}: {e}')
                        await session.rollback()  # Protect the database on failure


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
    session, tmdb: TMDBClient, show_title: str, local_year: int | None, cache
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
    session, tmdb: TMDBClient, show_id, show_tmdb_id, season_number, cache
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

    seasons_by_key[season_key] = season.id
    return season.id


async def _get_or_create_episode(
    session, season_id, show_tmdb_id, season_number, episode_number, cache
):
    """Handles finding or creating an Episode record."""
    stmt = select(Episode).where(
        Episode.season_id == season_id, Episode.episode_number == episode_number
    )
    result = await session.execute(stmt)
    episode = result.scalars().first()

    if not episode:
        tmdb_season_key = f'{show_tmdb_id}_{season_number}'

        # setdefault to ensure we safely access the cache
        tmdb_seasons = cache.setdefault('tmdb_seasons', {})
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
            title=ep_data.get('name', f'Episode {episode_number}')
            if ep_data
            else f'Episode {episode_number}',
            overview=ep_data.get('overview') if ep_data else None,
            still_path=ep_data.get('still_path') if ep_data else None,
        )
        session.add(episode)
        await session.flush()

    return episode.id


async def process_tv_file(
    file_path: Path, session, tmdb: TMDBClient, cache: dict[str, dict[Any, Any]]
):
    """Orchestrates the processing of a single TV episode file."""
    abs_path = str(file_path.absolute())

    # Skip if already in db
    stmt = select(MediaFile).where(MediaFile.file_path == abs_path)
    result = await session.execute(stmt)
    if result.scalars().first():
        logger.info(f'Skipping (already scanned): {file_path.name}')
        return

    # Extract metadata
    local_info = await asyncio.to_thread(extract_local_info, abs_path)
    show_title = local_info.get('title')
    season_number = _coerce_non_negative_int(local_info.get('season'))
    episode_number = _coerce_positive_int(local_info.get('episode'))
    local_year = _coerce_positive_int(local_info.get('year'))

    if not show_title or season_number is None or episode_number is None:
        logger.warning(f'Could not parse S/E from filename: {file_path.name}')
        return

    # Get/Create Show
    show_id, show_tmdb_id = await _get_or_create_tv_show(
        session, tmdb, show_title, local_year, cache
    )
    if not show_id:
        return

    # Get/Create Season
    season_id = await _get_or_create_season(
        session, tmdb, show_id, show_tmdb_id, season_number, cache
    )

    # Get/Create Episode (NEW CLEAN CALL)
    episode_id = await _get_or_create_episode(
        session, season_id, show_tmdb_id, season_number, episode_number, cache
    )

    # Link File
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


async def scan_tv_shows_directory(tv_shows_dir: str):
    """Walks the TV shows directory and orchestrates the scanning."""
    root_path = Path(tv_shows_dir)

    if not root_path.exists() or not root_path.is_dir():
        logger.error(f'Directory not found: {tv_shows_dir}')
        return

    async with TMDBClient() as tmdb:
        async with AsyncSessionLocal() as session:
            cache: dict[str, dict[Any, Any]] = {
                'shows_by_title': {},
                'seasons_by_key': {},
            }
            for file_path in root_path.rglob('*'):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in ALLOWED_EXTENSIONS
                ):
                    try:
                        await process_tv_file(file_path, session, tmdb, cache)
                    except Exception as e:
                        logger.error(f'Error processing {file_path.name}: {e}')
                        await session.rollback()


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


async def run_full_scan():
    """Reads all directories from the DB and scans them based on their type."""
    logger.info('Starting global background scan...')

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
                await scan_movies_directory(directory.path)
            elif directory.media_type == 'shows':
                await scan_tv_shows_directory(directory.path)

            # Update the last_scanned timestamp
            directory.last_scanned = get_brussels_time()
            session.add(directory)
            await session.commit()

        logger.info('--- Global Scan Complete ---')


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
