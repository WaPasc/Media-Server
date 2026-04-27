import logging
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
