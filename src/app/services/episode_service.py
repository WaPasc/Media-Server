from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.media import Credit, Episode, Season, TVShow


async def get_episode_by_id(db: AsyncSession, episode_id: int) -> Episode | None:
    """Loads an episode plus everything the detail screen needs: file/progress
    rows, the parent show with its show-level credits (to merge into the
    cast list), and the episode's own credits (guest stars).
    """
    stmt = (
        select(Episode)
        .where(Episode.id == episode_id)
        .options(
            selectinload(Episode.files),
            selectinload(Episode.progress),
            selectinload(Episode.credits).selectinload(Credit.person),
            selectinload(Episode.season)
            .selectinload(Season.show)
            .selectinload(TVShow.credits)
            .selectinload(Credit.person),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()
