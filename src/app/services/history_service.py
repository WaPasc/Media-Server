from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import Episode, Movie, Season
from app.models.user import WatchProgress


async def get_user_watch_history(db: AsyncSession, user_id: int) -> list[WatchProgress]:
    """Fetches all media the user has fully completed, ordered by most recently watched.

    Unlike continue-watching, this intentionally does NOT filter out rows whose
    catalog item was removed from the library, history is allowed to show
    'removed' entries (UI badges them).
    """

    stmt = (
        select(WatchProgress)
        .where(
            WatchProgress.user_id == user_id,
            WatchProgress.has_ever_completed,
        )
        .order_by(desc(WatchProgress.updated_at))
        .options(
            selectinload(WatchProgress.movie).options(
                selectinload(Movie.files),
                selectinload(Movie.progress),
            ),
            selectinload(WatchProgress.episode)
            .selectinload(Episode.season)
            .selectinload(Season.show),
            selectinload(WatchProgress.episode).selectinload(Episode.files),
        )
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())
