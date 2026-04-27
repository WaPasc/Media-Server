"""Integration test for the merged scan + availability behavior in
`scanner_service.run_full_scan`.

Verifies:
  * A MediaFile whose path still exists on disk stays is_available=True.
  * A MediaFile whose path vanished gets flipped to is_available=False.
  * A previously-missing file that reappeared is restored to True.
  * library_status is rolled up Movie / Episode → Season → TVShow.

Runs against a real Postgres (uses the same TEST_POSTGRES_URL gate as the
admin round-trip integration test). The schema is created and torn down
inside this test, so the target DB must be a throwaway.
"""

import os
from pathlib import Path
from typing import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_DB_URL = os.getenv('TEST_POSTGRES_URL')

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason='TEST_POSTGRES_URL not set, integration test skipped',
)

# Imports below depend on POSTGRES_URL being set, but our test uses its own
# engine, we never call the app's AsyncSessionLocal, only models + service.
os.environ.setdefault('POSTGRES_URL', TEST_DB_URL or 'postgresql://x:x@x/x')

from app.models.base import Base  # noqa: E402
from app.models.media import (  # noqa: E402
    Episode,
    MediaFile,
    Movie,
    ScanDirectory,
    Season,
    TVShow,
)
from app.models.user import UserShowProgress, WatchProgress  # noqa: E402, F401
from app.services import scanner_service  # noqa: E402


@pytest.fixture
async def engine():
    assert TEST_DB_URL is not None
    url = TEST_DB_URL.replace('postgresql://', 'postgresql+psycopg://')
    eng = create_async_engine(url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest.fixture
async def session_factory(
    engine, monkeypatch: pytest.MonkeyPatch
) -> async_sessionmaker[AsyncSession]:
    factory = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    # The scanner pulls AsyncSessionLocal from app.core.database; redirect it
    # to our test engine without touching the global module.
    monkeypatch.setattr(scanner_service, 'AsyncSessionLocal', factory)
    return factory


@pytest.fixture
def disable_tmdb(monkeypatch: pytest.MonkeyPatch) -> None:
    """The merged-scan test seeds catalog rows directly so the scanner only
    walks the disk for is_available reconciliation. Replace TMDBClient with
    a no-op context manager whose attribute access raises, proves no TMDB
    method is invoked while still letting the scanner enter/exit the cm.
    """

    class _NoTmdb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def __getattr__(self, name: str):
            raise AssertionError(f'TMDBClient.{name} should not be called in this test')

    monkeypatch.setattr(scanner_service, 'TMDBClient', lambda *a, **kw: _NoTmdb())


@pytest.fixture
async def scan_dirs(
    tmp_path: Path,
) -> AsyncIterator[tuple[Path, Path, Path, Path]]:
    movies_dir = tmp_path / 'movies'
    shows_dir = tmp_path / 'shows'
    movies_dir.mkdir()
    shows_dir.mkdir()

    on_disk_movie = movies_dir / 'present_movie.mp4'
    on_disk_movie.write_bytes(b'\x00')

    missing_movie_path = movies_dir / 'gone_movie.mp4'
    # Intentionally NOT created on disk.

    on_disk_episode = shows_dir / 'show_s01e01.mp4'
    on_disk_episode.write_bytes(b'\x00')

    missing_episode_path = shows_dir / 'show_s01e02.mp4'

    yield (
        on_disk_movie,
        missing_movie_path,
        on_disk_episode,
        missing_episode_path,
    )


async def test_run_full_scan_reconciles_availability_and_rollup(
    session_factory: async_sessionmaker[AsyncSession],
    disable_tmdb: None,
    scan_dirs: tuple[Path, Path, Path, Path],
) -> None:
    on_disk_movie, missing_movie, on_disk_ep, missing_ep = scan_dirs
    movies_root = str(on_disk_movie.parent.absolute())
    shows_root = str(on_disk_ep.parent.absolute())

    # Seed: two movies (one with file present, one with file missing), one
    # show with two episodes (one present, one missing).
    async with session_factory() as s:
        s.add_all(
            [
                ScanDirectory(path=movies_root, media_type='movies'),
                ScanDirectory(path=shows_root, media_type='shows'),
            ]
        )

        present_movie = Movie(title='Present Movie', library_status='present')
        gone_movie = Movie(title='Gone Movie', library_status='present')
        s.add_all([present_movie, gone_movie])
        await s.flush()

        s.add_all(
            [
                MediaFile(
                    file_path=str(on_disk_movie.absolute()),
                    movie_id=present_movie.id,
                    is_available=True,
                ),
                MediaFile(
                    file_path=str(missing_movie.absolute()),
                    movie_id=gone_movie.id,
                    is_available=True,
                ),
            ]
        )

        show = TVShow(title='Demo Show', library_status='present')
        s.add(show)
        await s.flush()
        season = Season(
            show_id=show.id,
            season_number=1,
            title='Season 1',
            library_status='present',
        )
        s.add(season)
        await s.flush()
        ep_present = Episode(
            season_id=season.id,
            season_number=1,
            episode_number=1,
            title='E1',
            library_status='present',
        )
        ep_gone = Episode(
            season_id=season.id,
            season_number=1,
            episode_number=2,
            title='E2',
            library_status='present',
        )
        s.add_all([ep_present, ep_gone])
        await s.flush()

        s.add_all(
            [
                MediaFile(
                    file_path=str(on_disk_ep.absolute()),
                    episode_id=ep_present.id,
                    is_available=True,
                ),
                MediaFile(
                    file_path=str(missing_ep.absolute()),
                    episode_id=ep_gone.id,
                    is_available=True,
                ),
            ]
        )

        await s.commit()

        present_movie_id = present_movie.id
        gone_movie_id = gone_movie.id
        show_id = show.id
        season_id = season.id
        ep_present_id = ep_present.id
        ep_gone_id = ep_gone.id

    await scanner_service.run_full_scan()

    async with session_factory() as s:
        files = (await s.execute(select(MediaFile))).scalars().all()
        by_path = {mf.file_path: mf for mf in files}

        assert by_path[str(on_disk_movie.absolute())].is_available is True
        assert by_path[str(missing_movie.absolute())].is_available is False
        assert by_path[str(on_disk_ep.absolute())].is_available is True
        assert by_path[str(missing_ep.absolute())].is_available is False

        present_movie_row = await s.get(Movie, present_movie_id)
        gone_movie_row = await s.get(Movie, gone_movie_id)
        assert present_movie_row is not None and gone_movie_row is not None
        assert present_movie_row.library_status == 'present'
        assert gone_movie_row.library_status == 'removed'

        ep_present_row = await s.get(Episode, ep_present_id)
        ep_gone_row = await s.get(Episode, ep_gone_id)
        assert ep_present_row is not None and ep_gone_row is not None
        assert ep_present_row.library_status == 'present'
        assert ep_gone_row.library_status == 'removed'

        # Season has at least one present episode → still 'present'.
        # Show has at least one present season → still 'present'.
        season_row = await s.get(Season, season_id)
        show_row = await s.get(TVShow, show_id)
        assert season_row is not None and show_row is not None
        assert season_row.library_status == 'present'
        assert show_row.library_status == 'present'


async def test_run_full_scan_restores_reappeared_file(
    session_factory: async_sessionmaker[AsyncSession],
    disable_tmdb: None,
    tmp_path: Path,
) -> None:
    movies_dir = tmp_path / 'movies'
    movies_dir.mkdir()
    movie_path = movies_dir / 'restored.mp4'
    movie_path.write_bytes(b'\x00')

    async with session_factory() as s:
        s.add(ScanDirectory(path=str(movies_dir.absolute()), media_type='movies'))
        # Movie was previously marked removed; file is back on disk now.
        movie = Movie(title='Restored', library_status='removed')
        s.add(movie)
        await s.flush()
        s.add(
            MediaFile(
                file_path=str(movie_path.absolute()),
                movie_id=movie.id,
                is_available=False,
            )
        )
        await s.commit()
        movie_id = movie.id

    await scanner_service.run_full_scan()

    async with session_factory() as s:
        mf = (
            await s.execute(
                select(MediaFile).where(
                    MediaFile.file_path == str(movie_path.absolute())
                )
            )
        ).scalar_one()
        assert mf.is_available is True

        movie_row = await s.get(Movie, movie_id)
        assert movie_row is not None
        assert movie_row.library_status == 'present'


async def test_run_availability_scan_reconciles_without_tmdb(
    session_factory: async_sessionmaker[AsyncSession],
    disable_tmdb: None,
    tmp_path: Path,
) -> None:
    """The standalone availability endpoint must flip is_available and roll
    up library_status without ever instantiating TMDBClient.
    """
    movies_dir = tmp_path / 'movies'
    movies_dir.mkdir()
    present_path = movies_dir / 'still_here.mp4'
    present_path.write_bytes(b'\x00')
    missing_path = movies_dir / 'gone.mp4'  # not created on disk

    async with session_factory() as s:
        s.add(ScanDirectory(path=str(movies_dir.absolute()), media_type='movies'))
        present_movie = Movie(title='Still Here', library_status='present')
        gone_movie = Movie(title='Gone', library_status='present')
        s.add_all([present_movie, gone_movie])
        await s.flush()
        s.add_all(
            [
                MediaFile(
                    file_path=str(present_path.absolute()),
                    movie_id=present_movie.id,
                    is_available=True,
                ),
                MediaFile(
                    file_path=str(missing_path.absolute()),
                    movie_id=gone_movie.id,
                    is_available=True,
                ),
            ]
        )
        await s.commit()
        gone_movie_id = gone_movie.id
        present_movie_id = present_movie.id

    await scanner_service.run_availability_scan()

    async with session_factory() as s:
        files = {
            mf.file_path: mf
            for mf in (await s.execute(select(MediaFile))).scalars().all()
        }
        assert files[str(present_path.absolute())].is_available is True
        assert files[str(missing_path.absolute())].is_available is False

        gone_movie_row = await s.get(Movie, gone_movie_id)
        present_movie_row = await s.get(Movie, present_movie_id)
        assert gone_movie_row is not None and present_movie_row is not None
        assert gone_movie_row.library_status == 'removed'
        assert present_movie_row.library_status == 'present'


async def test_run_full_scan_propagates_full_show_removal(
    session_factory: async_sessionmaker[AsyncSession],
    disable_tmdb: None,
    tmp_path: Path,
) -> None:
    shows_dir = tmp_path / 'shows'
    shows_dir.mkdir()
    # No files on disk; both episodes will be flipped to unavailable.
    ep1_path = shows_dir / 'show_s01e01.mp4'
    ep2_path = shows_dir / 'show_s01e02.mp4'

    async with session_factory() as s:
        s.add(ScanDirectory(path=str(shows_dir.absolute()), media_type='shows'))
        show = TVShow(title='Vanishing Show', library_status='present')
        s.add(show)
        await s.flush()
        season = Season(
            show_id=show.id,
            season_number=1,
            title='S1',
            library_status='present',
        )
        s.add(season)
        await s.flush()
        ep1 = Episode(
            season_id=season.id,
            season_number=1,
            episode_number=1,
            library_status='present',
        )
        ep2 = Episode(
            season_id=season.id,
            season_number=1,
            episode_number=2,
            library_status='present',
        )
        s.add_all([ep1, ep2])
        await s.flush()
        s.add_all(
            [
                MediaFile(
                    file_path=str(ep1_path.absolute()),
                    episode_id=ep1.id,
                    is_available=True,
                ),
                MediaFile(
                    file_path=str(ep2_path.absolute()),
                    episode_id=ep2.id,
                    is_available=True,
                ),
            ]
        )
        await s.commit()
        show_id = show.id
        season_id = season.id

    await scanner_service.run_full_scan()

    async with session_factory() as s:
        season_row = await s.get(Season, season_id)
        show_row = await s.get(TVShow, show_id)
        assert season_row is not None and show_row is not None
        assert season_row.library_status == 'removed'
        assert show_row.library_status == 'removed'
