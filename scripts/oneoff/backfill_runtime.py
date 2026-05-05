"""One-shot backfill for the runtime column on movies and episodes.

Run inside the backend container:
    docker exec -it ms-backend python -m app.migrations.backfill_runtime

Only touches rows where runtime IS NULL, so it's safe to re-run.
"""

import asyncio
import logging

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.media import Movie, Season, TVShow
from app.models.user import WatchProgress  # noqa: F401  (register mapper)
from app.services.tmdb_client import TMDBClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backfill_runtime')


async def backfill_movies(db, tmdb: TMDBClient) -> int:
    stmt = select(Movie).where(Movie.runtime.is_(None), Movie.tmdb_id.is_not(None))
    movies = (await db.execute(stmt)).scalars().all()

    updated = 0
    for movie in movies:
        try:
            data = await tmdb.get_movie(movie.tmdb_id)
        except Exception as e:
            logger.warning('TMDB get_movie(%s) failed: %s', movie.tmdb_id, e)
            continue

        runtime = data.get('runtime')
        if runtime:
            movie.runtime = runtime
            updated += 1
            logger.info('Movie %s -> %s min', movie.title, runtime)

    await db.commit()
    return updated


async def backfill_episodes(db, tmdb: TMDBClient) -> int:
    # Group by show -> season so we can use one season payload per season
    # rather than one /tv/{id}/season/{n}/episode/{m} call per episode.
    stmt = (
        select(TVShow)
        .options(selectinload(TVShow.seasons).selectinload(Season.episodes))
        .where(TVShow.tmdb_id.is_not(None))
    )
    shows = (await db.execute(stmt)).scalars().all()

    updated = 0
    for show in shows:
        for season in show.seasons:
            missing = [e for e in season.episodes if e.runtime is None]
            if not missing:
                continue

            try:
                payload = await tmdb.get_tv_season(show.tmdb_id, season.season_number)
            except Exception as e:
                logger.warning(
                    'TMDB get_tv_season(%s, %s) failed: %s',
                    show.tmdb_id,
                    season.season_number,
                    e,
                )
                continue

            by_num = {
                ep.get('episode_number'): ep for ep in payload.get('episodes', [])
            }
            for episode in missing:
                ep_data = by_num.get(episode.episode_number)
                runtime = ep_data.get('runtime') if ep_data else None
                if runtime:
                    episode.runtime = runtime
                    updated += 1

            logger.info(
                'Show %s S%02d: filled %d episode runtimes',
                show.title,
                season.season_number,
                sum(1 for e in missing if e.runtime is not None),
            )

    await db.commit()
    return updated


async def main():
    async with TMDBClient() as tmdb, AsyncSessionLocal() as db:
        movies_updated = await backfill_movies(db, tmdb)
        episodes_updated = await backfill_episodes(db, tmdb)

    logger.info(
        'Done. Movies updated: %d, episodes updated: %d',
        movies_updated,
        episodes_updated,
    )


if __name__ == '__main__':
    asyncio.run(main())
