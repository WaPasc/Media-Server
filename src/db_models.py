from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def get_brussels_time():
    """Returns a timezone-aware datetime for Brussels."""
    return datetime.now(ZoneInfo('Europe/Brussels'))


class Base(DeclarativeBase):
    pass


# ==========================================
# METADATA MODELS (Data from TMDB)
# ==========================================


class Movie(Base):
    __tablename__ = 'movies'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))  # Vertical
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))  # Horizontal

    # A single movie might have multiple files (e.g., 1080p and 4K versions)
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='movie', cascade='all, delete-orphan'
    )


class TVShow(Base):
    __tablename__ = 'tv_shows'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))

    # A show has many seasons
    seasons: Mapped[List['Season']] = relationship(
        back_populates='show', cascade='all, delete-orphan'
    )


class Season(Base):
    __tablename__ = 'seasons'

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(ForeignKey('tv_shows.id'))
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    season_number: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # e.g., "Season 1" or "Stranger Things 2"
    overview: Mapped[Optional[str]] = mapped_column(Text)

    # This is the main reason we need this table!
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))

    show: Mapped['TVShow'] = relationship(back_populates='seasons')

    # A season has many episodes
    episodes: Mapped[List['Episode']] = relationship(
        back_populates='season', cascade='all, delete-orphan'
    )


class Episode(Base):
    __tablename__ = 'episodes'

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey('seasons.id'))
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)

    # We still keep season_number here for easy sorting/querying without needing a join
    season_number: Mapped[int]
    episode_number: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(String(255))
    overview: Mapped[Optional[str]] = mapped_column(Text)

    # Episodes sometimes have their own "still" image from TMDB
    still_path: Mapped[Optional[str]] = mapped_column(String(255))

    season: Mapped['Season'] = relationship(back_populates='episodes')

    # Links to the actual physical file
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='episode', cascade='all, delete-orphan'
    )


# ==========================================
# PHYSICAL FILE MODEL (Data from ffprobe)
# ==========================================


class MediaFile(Base):
    __tablename__ = 'media_files'

    # 1. Enforce that a file is EITHER a movie OR an episode, but never both/neither.
    __table_args__ = (
        CheckConstraint(
            '(movie_id IS NULL AND episode_id IS NOT NULL) OR '
            '(movie_id IS NOT NULL AND episode_id IS NULL)',
            name='chk_movie_or_episode',
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String(1024), unique=True)
    duration: Mapped[Optional[float]]
    codec: Mapped[Optional[str]] = mapped_column(String(50))
    resolution: Mapped[Optional[str]] = mapped_column(String(50))

    movie_id: Mapped[Optional[int]] = mapped_column(ForeignKey('movies.id'))
    episode_id: Mapped[Optional[int]] = mapped_column(ForeignKey('episodes.id'))

    movie: Mapped[Optional['Movie']] = relationship(back_populates='files')
    episode: Mapped[Optional['Episode']] = relationship(back_populates='files')
    progress: Mapped[List['WatchProgress']] = relationship(
        back_populates='media_file', cascade='all, delete-orphan'
    )


# ==========================================
# USER DATA MODELS (Watch history & Bookmarks)
# ==========================================


class UserShowProgress(Base):
    """
    Tracks the highest level of progression a user has made in a specific TV Show.
    Used to quickly populate the 'Continue Watching' / 'Up Next' UI.
    """

    __tablename__ = 'user_show_progress'

    # 2. Prevent duplicate rows for the same user and show.
    __table_args__ = (UniqueConstraint('user_id', 'show_id', name='uix_user_show'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(default=1)  # Hardcoded to 1 for MVP
    show_id: Mapped[int] = mapped_column(ForeignKey('tv_shows.id'), index=True)

    last_watched_season_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('seasons.id')
    )
    last_watched_episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('episodes.id')
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
    user_id: Mapped[int] = mapped_column(default=1)  # Hardcoded to 1 for MVP
    media_file_id: Mapped[int] = mapped_column(ForeignKey('media_files.id'))

    stopped_at: Mapped[float] = mapped_column(Float, default=0.0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # 5. Timezone-aware, Brussels time
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time, onupdate=get_brussels_time
    )

    media_file: Mapped['MediaFile'] = relationship(back_populates='progress')
