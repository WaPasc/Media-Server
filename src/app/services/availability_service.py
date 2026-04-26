import logging
import os
from typing import List

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaFile, Movie, Season, TVShow

# Set up the logger
logger = logging.getLogger(__name__)


def _status_for_files(files: List[MediaFile]) -> str:
    """Map a set of MediaFiles to a catalog `library_status` value: 'present'
    if any file is on disk, 'removed' otherwise.
    """
    return 'present' if any(mf.is_available for mf in files) else 'removed'


async def _rollup_movie_availability(db: AsyncSession, movies_to_check: set[int]):
    """Recomputes library_status for movies based on whether any attached
    file is on disk.
    """
    if not movies_to_check:
        return

    movie_stmt = (
        select(Movie)
        .where(Movie.id.in_(movies_to_check))
        .options(selectinload(Movie.files))
    )
    movie_res = await db.execute(movie_stmt)

    for movie in movie_res.scalars().all():
        movie.library_status = _status_for_files(movie.files)
        db.add(movie)

    logger.info(f'Rolled up availability status for {len(movies_to_check)} movies.')


async def _rollup_episode_availability(
    db: AsyncSession, episodes_to_check: set[int]
) -> set[int]:
    """Recomputes library_status on episodes, and returns the set of season
    IDs whose status may have changed.
    """
    if not episodes_to_check:
        return set()

    ep_stmt = (
        select(Episode)
        .where(Episode.id.in_(episodes_to_check))
        .options(selectinload(Episode.files))
    )
    ep_res = await db.execute(ep_stmt)

    seasons_to_check: set[int] = set()
    for ep in ep_res.scalars().all():
        ep.library_status = _status_for_files(ep.files)
        db.add(ep)
        seasons_to_check.add(ep.season_id)

    logger.info(f'Rolled up availability status for {len(episodes_to_check)} episodes.')
    return seasons_to_check


async def _rollup_season_status(
    db: AsyncSession, seasons_to_check: set[int]
) -> set[int]:
    """Recomputes library_status for the given seasons using a single indexed
    EXISTS query per season, and returns the set of show IDs whose status may
    have changed.
    """
    if not seasons_to_check:
        return set()

    season_stmt = select(Season).where(Season.id.in_(seasons_to_check))
    season_res = await db.execute(season_stmt)

    shows_to_check: set[int] = set()
    for season in season_res.scalars().all():
        # One indexed btree probe via ix_episodes_season_status.
        any_present_stmt = select(
            exists().where(
                Episode.season_id == season.id,
                Episode.library_status == 'present',
            )
        )
        any_present = await db.scalar(any_present_stmt)
        new_status = 'present' if any_present else 'removed'
        if season.library_status != new_status:
            season.library_status = new_status
            db.add(season)
            shows_to_check.add(season.show_id)

    return shows_to_check


async def _rollup_show_status(db: AsyncSession, shows_to_check: set[int]) -> None:
    """Recomputes library_status for shows using a single indexed EXISTS query
    per show against seasons.
    """
    if not shows_to_check:
        return

    show_stmt = select(TVShow).where(TVShow.id.in_(shows_to_check))
    show_res = await db.execute(show_stmt)

    for show in show_res.scalars().all():
        # One indexed btree probe via ix_seasons_show_status.
        any_present_stmt = select(
            exists().where(
                Season.show_id == show.id,
                Season.library_status == 'present',
            )
        )
        any_present = await db.scalar(any_present_stmt)
        new_status = 'present' if any_present else 'removed'
        if show.library_status != new_status:
            show.library_status = new_status
            db.add(show)

    logger.info(f'Rolled up availability status for {len(shows_to_check)} shows.')


async def scan_library_availability(db: AsyncSession):
    """
    Checks if physical files still exist.
    Updates MediaFile.is_available (file-on-disk flag) and propagates to
    library_status on the catalog tables. Records are NOT deleted.

    Propagation order: MediaFile → Movie / Episode → Season → TVShow.
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

    # Update parent Movies and Episodes
    await _rollup_movie_availability(db, movies_to_check)
    seasons_to_check = await _rollup_episode_availability(db, episodes_to_check)

    # Flush so the EXISTS queries below see the just-updated episode statuses
    # within the same transaction.
    if seasons_to_check:
        await db.flush()

    # Propagate up: episodes → seasons → shows.
    shows_to_check = await _rollup_season_status(db, seasons_to_check)
    if shows_to_check:
        await db.flush()
    await _rollup_show_status(db, shows_to_check)

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
