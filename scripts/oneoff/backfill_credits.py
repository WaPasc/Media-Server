"""One-shot backfill: populate cast/credits for Movies, TVShows, and Episodes
already in the database.

Lives in src/app/migrations/ so it ships inside the backend image and can be
run via `docker exec`. After it has been run on every environment that needs
it, MOVE this file to scripts/oneoff/ so the next image build no longer
carries it;

Run inside the backend container:
    docker exec ms-backend bash -c \\
      "PYTHONPATH=/app/src /opt/venv/bin/python -m app.migrations.backfill_credits"

Idempotent: each sync_* call wipes and rewrites credits for one target, so
re-running is safe if it gets interrupted.
"""

import asyncio
import logging

from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.models.media import Episode, Movie, Season, TVShow
from app.models.user import UserShowProgress, WatchProgress  # noqa: F401
from app.services.credits_service import (
    sync_episode_credits,
    sync_movie_credits,
    sync_show_credits,
)
from app.services.tmdb_client import TMDBClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def _backfill_movies(tmdb: TMDBClient, background_tasks: set) -> int:
    async with AsyncSessionLocal() as session:
        rows = (
            (await session.execute(select(Movie).where(Movie.tmdb_id.is_not(None))))
            .scalars()
            .all()
        )
        logger.info('Backfilling credits for %d movies', len(rows))

        for i, movie in enumerate(rows, 1):
            assert movie.tmdb_id is not None  # SQL filter guarantees this
            await sync_movie_credits(
                session, tmdb, movie.id, movie.tmdb_id, background_tasks
            )
            if i % 25 == 0:
                await session.commit()
                logger.info('  movies: %d/%d', i, len(rows))

        await session.commit()
        return len(rows)


async def _backfill_shows(tmdb: TMDBClient, background_tasks: set) -> int:
    async with AsyncSessionLocal() as session:
        rows = (
            (await session.execute(select(TVShow).where(TVShow.tmdb_id.is_not(None))))
            .scalars()
            .all()
        )
        logger.info('Backfilling credits for %d shows', len(rows))

        for i, show in enumerate(rows, 1):
            assert show.tmdb_id is not None  # SQL filter guarantees this
            await sync_show_credits(
                session, tmdb, show.id, show.tmdb_id, background_tasks
            )
            if i % 10 == 0:
                await session.commit()
                logger.info('  shows: %d/%d', i, len(rows))

        await session.commit()
        return len(rows)


async def _backfill_episodes(tmdb: TMDBClient, background_tasks: set) -> int:
    async with AsyncSessionLocal() as session:
        # Need show_tmdb_id and season_number alongside the episode itself,
        # so join through Season -> TVShow once instead of per-episode lookups.
        stmt = (
            select(Episode, Season.season_number, TVShow.tmdb_id)
            .join(Season, Episode.season_id == Season.id)
            .join(TVShow, Season.show_id == TVShow.id)
            .where(TVShow.tmdb_id.is_not(None))
        )
        rows = (await session.execute(stmt)).all()
        logger.info('Backfilling credits for %d episodes', len(rows))

        for i, (episode, season_number, show_tmdb_id) in enumerate(rows, 1):
            await sync_episode_credits(
                session,
                tmdb,
                episode.id,
                show_tmdb_id,
                season_number,
                episode.episode_number,
                background_tasks,
            )
            if i % 50 == 0:
                await session.commit()
                logger.info('  episodes: %d/%d', i, len(rows))

        await session.commit()
        return len(rows)


async def main() -> None:
    background_tasks: set = set()

    async with TMDBClient() as tmdb:
        n_movies = await _backfill_movies(tmdb, background_tasks)
        n_shows = await _backfill_shows(tmdb, background_tasks)
        n_episodes = await _backfill_episodes(tmdb, background_tasks)

        if background_tasks:
            logger.info(
                'Waiting for %d profile-image mirrors to finish',
                len(background_tasks),
            )
            await asyncio.gather(*background_tasks, return_exceptions=True)

    logger.info(
        'Backfill complete: %d movies, %d shows, %d episodes',
        n_movies,
        n_shows,
        n_episodes,
    )


if __name__ == '__main__':
    asyncio.run(main())
