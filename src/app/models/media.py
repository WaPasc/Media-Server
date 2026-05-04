from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.utils.datetime import get_brussels_time

if TYPE_CHECKING:
    from app.models.user import WatchProgress

# Catalog availability states. `present` = at least one playable file on disk.
# `removed` = used to be in library, file is gone, watch state preserved.
# `placeholder` = TMDB-known but no file yet (partial seasons, future use).
LIBRARY_STATUS_VALUES = ('present', 'removed', 'placeholder')
_LIBRARY_STATUS_CHECK = "library_status IN ('present', 'removed', 'placeholder')"


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

    movie_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('movies.id', ondelete='CASCADE'), index=True
    )

    episode_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('episodes.id', ondelete='CASCADE'), index=True
    )

    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Stamped (UTC) when the scanner first finds the file missing on disk;
    # cleared when the file reappears. A daily sweep hard-deletes rows whose
    # deleted_at is older than the grace period, so soft-deletes don't pile
    # up forever. Keep is_available as the source of truth for "playable
    # right now"; deleted_at only drives cleanup.
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    movie: Mapped[Optional['Movie']] = relationship(back_populates='files')
    episode: Mapped[Optional['Episode']] = relationship(back_populates='files')


class Movie(Base):
    __tablename__ = 'movies'
    __table_args__ = (
        CheckConstraint(_LIBRARY_STATUS_CHECK, name='chk_movies_library_status'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))  # Vertical
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))  # Horizontal

    # Runtime in minutes, sourced from TMDB.
    runtime: Mapped[Optional[int]]

    # IMDb identifier (e.g. "tt0133093"), cached from TMDB. The actual
    # rating is looked up at read time against the imdb_ratings dataset
    # table (see app.models.imdb).
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), index=True)

    library_status: Mapped[str] = mapped_column(
        String(20), default='present', nullable=False, index=True
    )

    # A single movie might have multiple files (e.g., 1080p and 4K versions)
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='movie',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    progress: Mapped[List['WatchProgress']] = relationship(
        back_populates='movie',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    credits: Mapped[List['Credit']] = relationship(
        back_populates='movie',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class Episode(Base):
    __tablename__ = 'episodes'
    __table_args__ = (
        CheckConstraint(_LIBRARY_STATUS_CHECK, name='chk_episodes_library_status'),
        # Composite index drives the season-rollup EXISTS query: "any present
        # episode in this season?". Single btree probe.
        Index('ix_episodes_season_status', 'season_id', 'library_status'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey('seasons.id', ondelete='CASCADE'), index=True
    )
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)

    # We still keep season_number here for easy sorting/querying without needing a join
    season_number: Mapped[int]
    episode_number: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(String(255))
    overview: Mapped[Optional[str]] = mapped_column(Text)

    # Episodes sometimes have their own "still" image from TMDB
    still_path: Mapped[Optional[str]] = mapped_column(String(255))

    # Runtime in minutes, sourced from the per-episode entry on TMDB's
    # /tv/{id}/season/{n} payload.
    runtime: Mapped[Optional[int]]

    # IMDb identifier (cached from TMDB). Episodes have their own IMDb
    # IDs distinct from the parent show. Rating is looked up from the
    # imdb_ratings dataset table at read time.
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), index=True)

    season: Mapped['Season'] = relationship(back_populates='episodes')

    library_status: Mapped[str] = mapped_column(
        String(20), default='present', nullable=False
    )

    # Links to the actual physical file
    files: Mapped[List['MediaFile']] = relationship(
        back_populates='episode',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    progress: Mapped[List['WatchProgress']] = relationship(
        back_populates='episode',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class Season(Base):
    __tablename__ = 'seasons'
    __table_args__ = (
        CheckConstraint(_LIBRARY_STATUS_CHECK, name='chk_seasons_library_status'),
        # Composite index drives the show-rollup EXISTS query: "any present
        # season in this show?".
        Index('ix_seasons_show_status', 'show_id', 'library_status'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    show_id: Mapped[int] = mapped_column(
        ForeignKey('tv_shows.id', ondelete='CASCADE'), index=True
    )
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    season_number: Mapped[int]
    title: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # e.g., "Season 1" or "Stranger Things 2"
    overview: Mapped[Optional[str]] = mapped_column(Text)

    # This is the main reason we need this table!
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))

    library_status: Mapped[str] = mapped_column(
        String(20), default='present', nullable=False
    )

    show: Mapped['TVShow'] = relationship(back_populates='seasons')

    # A season has many episodes
    episodes: Mapped[List['Episode']] = relationship(
        back_populates='season',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class TVShow(Base):
    __tablename__ = 'tv_shows'
    __table_args__ = (
        CheckConstraint(_LIBRARY_STATUS_CHECK, name='chk_tv_shows_library_status'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[Optional[int]]
    overview: Mapped[Optional[str]] = mapped_column(Text)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255))
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255))

    library_status: Mapped[str] = mapped_column(
        String(20), default='present', nullable=False, index=True
    )

    # A show has many seasons
    seasons: Mapped[List['Season']] = relationship(
        back_populates='show',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    credits: Mapped[List['Credit']] = relationship(
        back_populates='show',
        cascade='all, delete-orphan',
        passive_deletes=True,
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


class Person(Base):
    __tablename__ = 'people'

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    # TMDB profile image path (e.g. "/abc123.jpg"). The full URL is built at
    # read time via TMDBClient.get_profile_url, or eventually mirrored to S3
    # the same way posters/backdrops are.
    profile_path: Mapped[Optional[str]] = mapped_column(String(255))

    credits: Mapped[List['Credit']] = relationship(
        back_populates='person',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class Credit(Base):
    """Cast credit linking a Person to either a Movie or a TVShow.

    Episode-level guest credits are intentionally out of scope for v1; if we
    ever want them, add a nullable episode_id and broaden the CHECK.
    """

    __tablename__ = 'credits'
    __table_args__ = (
        CheckConstraint(
            '(movie_id IS NULL AND show_id IS NOT NULL) OR '
            '(movie_id IS NOT NULL AND show_id IS NULL)',
            name='chk_credit_movie_or_show',
        ),
        # The same person can appear once per title, but might play multiple
        # roles (e.g. dual characters). Don't constrain (person_id, title)
        # uniqueness here — let the scanner replace credits wholesale per
        # title instead.
        #
        # Partial indexes: a credit row has either movie_id or show_id, never
        # both. Excluding the NULL half keeps each index lean and skips rows
        # the corresponding query path will never touch.
        Index(
            'ix_credits_movie_order',
            'movie_id',
            'cast_order',
            postgresql_where=text('movie_id IS NOT NULL'),
        ),
        Index(
            'ix_credits_show_episode_count',
            'show_id',
            'episode_count',
            postgresql_where=text('show_id IS NOT NULL'),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    person_id: Mapped[int] = mapped_column(
        ForeignKey('people.id', ondelete='CASCADE'), index=True
    )

    movie_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('movies.id', ondelete='CASCADE')
    )
    show_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('tv_shows.id', ondelete='CASCADE')
    )

    character: Mapped[Optional[str]] = mapped_column(String(255))

    # TMDB's `order` field — lower = more prominent billing. Drives the
    # default cast list ordering on movie detail screens.
    cast_order: Mapped[Optional[int]]

    # Populated for show credits from /aggregate_credits.total_episode_count;
    # NULL for movie credits. Drives the default cast list ordering on show
    # detail screens (most-recurring actor first).
    episode_count: Mapped[Optional[int]]

    person: Mapped['Person'] = relationship(back_populates='credits')
    movie: Mapped[Optional['Movie']] = relationship(back_populates='credits')
    show: Mapped[Optional['TVShow']] = relationship(back_populates='credits')
