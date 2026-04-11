from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.media import Episode, MediaFile, Season, TVShow
from app.services.tmdb_client import TMDBClient


async def get_all_shows(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> list[TVShow]:
    stmt = select(TVShow).offset(skip).limit(limit)
    result = await db.execute(stmt)
    shows = result.scalars().all()

    return shows


async def get_show_by_id(db: AsyncSession, show_id: int) -> TVShow | None:
    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id)
        .options(
            selectinload(TVShow.seasons)
            .selectinload(Season.episodes)
            .selectinload(Episode.files)
            .selectinload(MediaFile.progress)
        )
    )
    result = await db.execute(stmt)
    show = result.scalars().first()

    return show


async def refresh_show_metadata(db: AsyncSession, tmdb: TMDBClient, show_id: int):
    # 1. Fetch the show with all its nested relations
    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id)
        .options(selectinload(TVShow.seasons).selectinload(Season.episodes))
    )
    result = await db.execute(stmt)
    show = result.scalars().first()

    if not show or not show.tmdb_id:
        return None

    # 2. Update Top-Level Show Metadata
    data = await tmdb.get_tv_show(show.tmdb_id)
    show.title = data.get('name', show.title)
    show.overview = data.get('overview', show.overview)
    show.poster_path = data.get('poster_path', show.poster_path)
    show.backdrop_path = data.get('backdrop_path', show.backdrop_path)

    # 3. Update Seasons and Episodes
    for season_data in data.get('seasons', []):
        season_num = season_data.get('season_number')

        # Find existing season in our DB
        season = next((s for s in show.seasons if s.season_number == season_num), None)
        if not season:
            continue

        # Fetch full season details to get episode-level overview/images
        full_season_data = await tmdb.get_tv_season(show.tmdb_id, season_num)

        season.title = full_season_data.get('name', season.title)
        season.overview = full_season_data.get('overview', season.overview)
        season.poster_path = full_season_data.get('poster_path', season.poster_path)

        # 4. Update Episodes within that season
        for ep_data in full_season_data.get('episodes', []):
            ep_num = ep_data.get('episode_number')
            episode = next(
                (e for e in season.episodes if e.episode_number == ep_num), None
            )

            if episode:
                episode.title = ep_data.get('name', episode.title)
                episode.overview = ep_data.get('overview', episode.overview)
                episode.still_path = ep_data.get('still_path', episode.still_path)

    await db.commit()
    return show
