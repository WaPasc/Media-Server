"""IMDb non-commercial ratings dataset.

Downloads `title.ratings.tsv.gz` from https://datasets.imdbws.com/ and
ingests it into the `imdb_ratings` table. Free for personal/non-commercial
use; weekly refresh is sufficient, the dataset is regenerated daily by
IMDb but ratings move slowly.

Set-and-forget: app startup checks the local file's mtime and triggers a
background refresh if it's missing or older than `MAX_AGE_DAYS`. Failures
during download/ingest log a warning and leave the previous data intact.
"""

import asyncio
import gzip
import logging
import queue
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.imdb import ImdbRating

logger = logging.getLogger(__name__)

DATASET_URL = 'https://datasets.imdbws.com/title.ratings.tsv.gz'
DATASET_DIR = Path('/app/data/imdb')
DATASET_FILE = DATASET_DIR / 'title.ratings.tsv.gz'
MAX_AGE_DAYS = 7
BATCH_SIZE = 5000
# Commit every N rows so we don't hold row locks + bloat WAL across the
# whole 1.6M-row ingest. Reference data, so a partial commit is fine.
COMMIT_EVERY = 100_000


async def _download_dataset(target: Path) -> None:
    """Stream the gzipped dataset to disk via a .tmp + atomic rename so a
    partial download can never replace a good file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + '.tmp')

    logger.info('Downloading IMDb ratings dataset from %s', DATASET_URL)
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        async with client.stream('GET', DATASET_URL) as response:
            response.raise_for_status()
            with tmp.open('wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)

    tmp.replace(target)
    logger.info('IMDb ratings dataset saved to %s', target)


_END_OF_STREAM = object()  # sentinel: pushed by producer when TSV is exhausted


def _produce_batches(
    path: Path, now: datetime, batch_size: int, out: 'queue.Queue'
) -> None:
    """Sync producer: stream the gzipped TSV and push BATCH_SIZE-row
    chunks into `out`. Runs in a worker thread. Pushes _END_OF_STREAM
    when done (or on error after re-raising into the queue) so the
    async consumer knows to stop.

    Memory: only one in-flight batch held here at a time; the queue's
    maxsize bounds how many sit waiting for the DB.
    """
    try:
        batch: list[dict] = []
        with gzip.open(path, mode='rt', encoding='utf-8') as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) < 3:
                    continue
                tconst, rating_s, votes_s = parts[0], parts[1], parts[2]
                try:
                    rating = float(rating_s)
                except ValueError:
                    continue
                try:
                    votes = int(votes_s)
                except ValueError:
                    votes = None
                batch.append(
                    {
                        'tconst': tconst,
                        'rating': rating,
                        'votes': votes,
                        'updated_at': now,
                    }
                )
                if len(batch) >= batch_size:
                    out.put(batch)
                    batch = []
        if batch:
            out.put(batch)
    finally:
        out.put(_END_OF_STREAM)


async def _ingest_dataset(session: AsyncSession, path: Path) -> int:
    """Upsert every row in the TSV into imdb_ratings via a streaming
    producer/consumer pipeline with periodic commits.

    A worker thread reads + parses the gzipped TSV in batches and pushes
    them through a bounded queue (maxsize=4 batches ≈ 1.4 MB peak). The
    event loop drains the queue, awaits each upsert, and never holds
    more than ~5 batches' worth of rows in memory at once.

    Bounded queue acts as backpressure, the thread blocks on `put()`
    when the DB falls behind, so we never read faster than we ingest.

    Commits happen every COMMIT_EVERY rows so we don't sit on a giant
    transaction holding row locks + bloating WAL across 1.6M upserts.
    The dataset is reference data, so a partial commit is harmless, a
    crash mid-ingest just means the next refresh finishes the rest.
    """
    now = datetime.now(timezone.utc)
    batch_queue: queue.Queue = queue.Queue(maxsize=4)
    loop = asyncio.get_running_loop()

    producer = loop.run_in_executor(
        None, _produce_batches, path, now, BATCH_SIZE, batch_queue
    )

    total = 0
    uncommitted = 0
    try:
        while True:
            # Block-on-get must run in a thread so we don't pin the loop.
            item = await loop.run_in_executor(None, batch_queue.get)
            if item is _END_OF_STREAM:
                break
            stmt = pg_insert(ImdbRating).values(item)
            stmt = stmt.on_conflict_do_update(
                index_elements=[ImdbRating.tconst],
                set_={
                    'rating': stmt.excluded.rating,
                    'votes': stmt.excluded.votes,
                    'updated_at': stmt.excluded.updated_at,
                },
            )
            await session.execute(stmt)
            total += len(item)
            uncommitted += len(item)

            if uncommitted >= COMMIT_EVERY:
                await session.commit()
                uncommitted = 0
    finally:
        # Surface any exception raised inside the producer thread.
        await producer

    # Flush whatever's left below the COMMIT_EVERY threshold.
    if uncommitted:
        await session.commit()
    return total


async def _file_age_days(path: Path) -> float | None:
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).total_seconds() / 86400


async def refresh(force: bool = False) -> dict:
    """Download (if needed) and ingest the dataset. Returns a small
    summary dict. Safe to call concurrently, Postgres serialises the
    upsert and the file replace is atomic.
    """
    age = await _file_age_days(DATASET_FILE)
    needs_download = force or age is None or age >= MAX_AGE_DAYS

    if needs_download:
        try:
            await _download_dataset(DATASET_FILE)
        except (httpx.HTTPError, OSError) as e:
            logger.warning('IMDb dataset download failed: %s', e)
            return {'downloaded': False, 'ingested': 0, 'error': str(e)}

    try:
        async with AsyncSessionLocal() as session:
            ingested = await _ingest_dataset(session, DATASET_FILE)
    except (OSError, gzip.BadGzipFile) as e:
        logger.warning('IMDb dataset ingest failed: %s', e)
        return {'downloaded': needs_download, 'ingested': 0, 'error': str(e)}

    logger.info('IMDb dataset ingest complete: %d rows', ingested)
    return {'downloaded': needs_download, 'ingested': ingested}


async def refresh_if_stale() -> None:
    """Background-task entry point. Trigger conditions:
    - imdb_ratings table is empty (first run after migration), OR
    - local TSV file is missing or older than MAX_AGE_DAYS.

    The DB-emptiness check covers the case where someone wipes the
    table but the file is still on disk, we still want to re-ingest.
    """
    try:
        async with AsyncSessionLocal() as session:
            row_count = await session.scalar(
                select(func.count()).select_from(ImdbRating)
            )
    except Exception as e:
        logger.warning('IMDb dataset: could not query row count: %s', e)
        return

    age = await _file_age_days(DATASET_FILE)
    file_stale = age is None or age >= MAX_AGE_DAYS

    if row_count and not file_stale:
        logger.info(
            'IMDb dataset fresh (%d rows, file age %.1fd), skipping refresh',
            row_count,
            age or 0.0,
        )
        return

    logger.info(
        'IMDb dataset refresh triggered (rows=%s, file_age_days=%s)',
        row_count,
        f'{age:.1f}' if age is not None else 'missing',
    )
    await refresh(force=False)


async def get_ratings_for_imdb_ids(
    session: AsyncSession, imdb_ids: list[str]
) -> dict[str, float]:
    """Batched lookup used by the response builders. Returns
    `{tconst: rating}`. Unknown tconsts are simply absent.
    """
    if not imdb_ids:
        return {}
    stmt = select(ImdbRating.tconst, ImdbRating.rating).where(
        ImdbRating.tconst.in_(imdb_ids)
    )
    result = await session.execute(stmt)
    return {row.tconst: row.rating for row in result}
