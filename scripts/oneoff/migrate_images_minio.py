# src/migrations/migrate_images_minio.py

import asyncio
import logging

from sqlalchemy.future import select

from app.core.constants import TMDB_BACKDROP_SIZE, TMDB_POSTER_SIZE, TMDB_STILL_SIZE
from app.core.database import AsyncSessionLocal
from app.models.media import Episode, MediaFile, Movie, Season, TVShow  # noqa: F401
from app.models.user import WatchProgress  # noqa: F401
from app.services.minio_service import ensure_image_in_minio

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def migrate_existing_images():
    logger.info('Starting image migration to MinIO...')

    async with AsyncSessionLocal() as session:
        # We will collect all download tasks here to run them concurrently
        download_tasks = []

        # 1. Gather Movie Images
        logger.info('--- Gathering Movies ---')
        result = await session.execute(select(Movie))
        movies = result.scalars().all()
        for movie in movies:
            if movie.poster_path:
                download_tasks.append(
                    ensure_image_in_minio(movie.poster_path, TMDB_POSTER_SIZE)
                )
            if movie.backdrop_path:
                download_tasks.append(
                    ensure_image_in_minio(movie.backdrop_path, TMDB_BACKDROP_SIZE)
                )

        # 2. Gather TV Show Images
        logger.info('--- Gathering TV Shows ---')
        result = await session.execute(select(TVShow))
        shows = result.scalars().all()
        for show in shows:
            if show.poster_path:
                download_tasks.append(
                    ensure_image_in_minio(show.poster_path, TMDB_POSTER_SIZE)
                )
            if show.backdrop_path:
                download_tasks.append(
                    ensure_image_in_minio(show.backdrop_path, TMDB_BACKDROP_SIZE)
                )

        # 3. Gather Season Images
        logger.info('--- Gathering Seasons ---')
        result = await session.execute(select(Season))
        seasons = result.scalars().all()
        for season in seasons:
            if season.poster_path:
                download_tasks.append(
                    ensure_image_in_minio(season.poster_path, TMDB_POSTER_SIZE)
                )

        # 4. Gather Episode Images
        logger.info('--- Gathering Episodes ---')
        result = await session.execute(select(Episode))
        episodes = result.scalars().all()
        for episode in episodes:
            if episode.still_path:
                download_tasks.append(
                    ensure_image_in_minio(episode.still_path, TMDB_STILL_SIZE)
                )

        # 5. Execute all downloads concurrently (protected by Semaphore)
        if download_tasks:
            logger.info(
                f'Executing {len(download_tasks)} downloads concurrently (Max 10 at a time)...'
            )
            # return_exceptions=True ensures one missing TMDB image doesn't crash the whole migration
            await asyncio.gather(*download_tasks, return_exceptions=True)

    logger.info('Migration complete! All images are now stored in MinIO.')


if __name__ == '__main__':
    asyncio.run(migrate_existing_images())
