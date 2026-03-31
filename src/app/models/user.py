from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.utils.datetime import get_brussels_time

if TYPE_CHECKING:
    from app.models.media import Episode, MediaFile, Season, TVShow


class UserShowProgress(Base):
    """
    Tracks the highest level of progression a user has made in a specific TV Show.
    Used to quickly populate the 'Continue Watching' / 'Up Next' UI.
    """

    __tablename__ = 'user_show_progress'

    # 2. Prevent duplicate rows for the same user and show.
    __table_args__ = (UniqueConstraint('user_id', 'show_id', name='uix_user_show'),)

    id: Mapped[int] = mapped_column(primary_key=True)

    # Added index=True for fast lookups per user
    user_id: Mapped[int] = mapped_column(
        default=1, index=True
    )  # Hardcoded to 1 for MVP

    # Added ondelete='CASCADE'
    show_id: Mapped[int] = mapped_column(
        ForeignKey('tv_shows.id', ondelete='CASCADE'), index=True
    )

    # Added index=True and ondelete='CASCADE'
    last_watched_season_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('seasons.id', ondelete='CASCADE'), index=True
    )
    last_watched_episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('episodes.id', ondelete='CASCADE'), index=True
    )

    # 3. Timezone-aware, Brussels time
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time, onupdate=get_brussels_time
    )

    show: Mapped['TVShow'] = relationship()
    season: Mapped[Optional['Season']] = relationship()
    episode: Mapped[Optional['Episode']] = relationship()


class WatchProgress(Base):
    __tablename__ = 'watch_progress'

    # 4. Prevent duplicate rows for the same user and file.
    __table_args__ = (
        UniqueConstraint('user_id', 'media_file_id', name='uix_user_media_file'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Added index=True
    user_id: Mapped[int] = mapped_column(
        default=1, index=True
    )  # Hardcoded to 1 for MVP

    # Added index=True and ondelete='CASCADE'
    media_file_id: Mapped[int] = mapped_column(
        ForeignKey('media_files.id', ondelete='CASCADE'), index=True
    )

    stopped_at: Mapped[float] = mapped_column(Float, default=0.0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ever_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # 5. Timezone-aware, Brussels time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time, onupdate=get_brussels_time
    )

    media_file: Mapped['MediaFile'] = relationship(back_populates='progress')
