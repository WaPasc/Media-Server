import asyncio
import logging
from pathlib import Path

from sqlalchemy.future import select

from database import AsyncSessionLocal
from db_models import MediaFile, Movie
from metadata import extract_local_info
from tmdb_client import TMDBClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.webm'}


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


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python scanner.py /path/to/movies')
    else:
        asyncio.run(scan_movies_directory(sys.argv[1]))
