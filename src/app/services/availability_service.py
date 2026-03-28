import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaFile, Movie

# Set up the logger
logger = logging.getLogger(__name__)


async def scan_library_availability(db: AsyncSession):
    """
    Checks if physical files still exist.
    Updates the is_available flags WITHOUT deleting the records.
    """
    logger.info('Starting library availability scan...')

    # Fetch all files and their current status
    stmt = select(MediaFile)
    result = await db.execute(stmt)
    files = result.scalars().all()

    movies_to_check = set()
    episodes_to_check = set()

    files_marked_missing = 0
    files_marked_found = 0

    # Check the filesystem
    for f in files:
        file_exists = os.path.exists(f.file_path)

        # Did the status change?
        if file_exists != f.is_available:
            f.is_available = file_exists
            db.add(f)  # Queue the update

            # Log the exact file changes
            if file_exists:
                logger.info(f'File restored: {f.file_path}')
                files_marked_found += 1
            else:
                logger.warning(f'File missing: {f.file_path}')
                files_marked_missing += 1

            # Note the parent IDs so we can update them next
            if f.movie_id:
                movies_to_check.add(f.movie_id)
            if f.episode_id:
                episodes_to_check.add(f.episode_id)

    # Update the Parent Movies
    if movies_to_check:
        # selectinload(Movie.files) so the async session doesn't crash
        movie_stmt = (
            select(Movie)
            .where(Movie.id.in_(movies_to_check))
            .options(selectinload(Movie.files))
        )
        movie_res = await db.execute(movie_stmt)

        for movie in movie_res.scalars().all():
            # A movie is available if any of its files are available
            movie.is_available = any(mf.is_available for mf in movie.files)
            db.add(movie)

        logger.info(f'Rolled up availability status for {len(movies_to_check)} movies.')

    # Update the Parent Episodes
    if episodes_to_check:
        ep_stmt = (
            select(Episode)
            .where(Episode.id.in_(episodes_to_check))
            .options(selectinload(Episode.files))
        )
        ep_res = await db.execute(ep_stmt)

        for ep in ep_res.scalars().all():
            ep.is_available = any(mf.is_available for mf in ep.files)
            db.add(ep)

        logger.info(
            f'Rolled up availability status for {len(episodes_to_check)} episodes.'
        )

    # Commit all changes at once
    if files_marked_missing > 0 or files_marked_found > 0:
        await db.commit()
        logger.info(
            f'Scan complete. Missing: {files_marked_missing} | Restored: {files_marked_found}'
        )
    else:
        logger.info(
            'Scan complete. All files are perfectly matching the database state.'
        )
