from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.utils.datetime import get_brussels_time

if TYPE_CHECKING:
    from app.models.user import WatchProgress


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

    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    movie: Mapped[Optional['Movie']] = relationship(back_populates='files')
    episode: Mapped[Optional['Episode']] = relationship(back_populates='files')
    progress: Mapped[List['WatchProgress']] = relationship(
        back_populates='media_file', cascade='all, delete-orphan'
    )


class Movie(Base):
    __tablename__ = 'movies'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))  # Vertical
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))  # Horizontal

    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    # A single movie might have multiple files (e.g., 1080p and 4K versions)
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='movie', cascade='all, delete-orphan'
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

    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Links to the actual physical file
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='episode', cascade='all, delete-orphan'
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


class TVShow(Base):
    __tablename__ = 'tv_shows'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))

    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    # A show has many seasons
    seasons: Mapped[List['Season']] = relationship(
        back_populates='show', cascade='all, delete-orphan'
    )


class ScanDirectory(Base):
    __tablename__ = 'scan_directories'

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(1024), unique=True)
    # movies or shows
    media_type: Mapped[str] = mapped_column(String(20))

    last_scanned: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_brussels_time
    )
