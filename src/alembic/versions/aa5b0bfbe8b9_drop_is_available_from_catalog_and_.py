"""drop is_available from catalog and media_file_id from watch_progress

Revision ID: aa5b0bfbe8b9
Revises: de12da6d2329
Create Date: 2026-04-26 23:14:50.033884

Contracts the schema after our previous dual-write window:
  * watch_progress.media_file_id is dropped; reads now go through
    movie_id / episode_id.
  * The (user, media_file) unique constraint is replaced with two partial
    unique indexes on (user, movie) / (user, episode).
  * The catalog-target CHECK is tightened to "exactly one of movie_id /
    episode_id is set" (NULL/NULL no longer tolerated).
  * is_available is removed from movies / tv_shows / episodes; library_status
    is now the single source of truth on the catalog side. MediaFile keeps
    its own is_available (file-on-disk flag).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'aa5b0bfbe8b9'
down_revision: Union[str, Sequence[str], None] = 'de12da6d2329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_CATALOG_TARGET_CHECK = (
    '(movie_id IS NULL AND episode_id IS NOT NULL) OR '
    '(movie_id IS NOT NULL AND episode_id IS NULL)'
)
_OLD_CATALOG_TARGET_CHECK = (
    '(movie_id IS NULL AND episode_id IS NOT NULL) OR '
    '(movie_id IS NOT NULL AND episode_id IS NULL) OR '
    '(movie_id IS NULL AND episode_id IS NULL)'
)


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop the old (user, media_file) unique constraint and the lookup
    #    index on media_file_id; reads no longer use that column.
    op.drop_constraint(op.f('uix_user_media_file'), 'watch_progress', type_='unique')
    op.drop_index(op.f('ix_watch_progress_media_file_id'), table_name='watch_progress')

    # 2. Drop the old composite indexes that we previously added; the partial uniques
    #    we create below replace them (one btree per pair, both serve lookup
    #    AND uniqueness).
    op.drop_index(op.f('ix_watch_progress_user_episode'), table_name='watch_progress')
    op.drop_index(op.f('ix_watch_progress_user_movie'), table_name='watch_progress')

    # 3. Drop the old (permissive) CHECK before the column drop, then sweep
    #    any orphan rows that somehow ended up NULL/NULL during dual-write
    #    (defensive — should be 0 after previous backfill).
    op.drop_constraint(
        'chk_watch_progress_catalog_target', 'watch_progress', type_='check'
    )
    op.execute(
        sa.text(
            'DELETE FROM watch_progress WHERE movie_id IS NULL AND episode_id IS NULL'
        )
    )

    # 4. Drop the FK and the column itself. Done before the new CHECK so the
    #    new constraint is evaluated only against the post-cleanup rows.
    op.drop_constraint(
        op.f('watch_progress_media_file_id_fkey'),
        'watch_progress',
        type_='foreignkey',
    )
    op.drop_column('watch_progress', 'media_file_id')

    # 5. Tighter CHECK: exactly one of movie_id / episode_id is set.
    op.create_check_constraint(
        'chk_watch_progress_catalog_target',
        'watch_progress',
        _NEW_CATALOG_TARGET_CHECK,
    )

    # 6. Partial unique indexes — one progress row per (user, catalog item).
    op.create_index(
        'uix_user_movie',
        'watch_progress',
        ['user_id', 'movie_id'],
        unique=True,
        postgresql_where=sa.text('movie_id IS NOT NULL'),
    )
    op.create_index(
        'uix_user_episode',
        'watch_progress',
        ['user_id', 'episode_id'],
        unique=True,
        postgresql_where=sa.text('episode_id IS NOT NULL'),
    )

    # 7. Drop is_available from the catalog tables. library_status is now
    #    authoritative on this side; MediaFile.is_available stays.
    op.drop_column('episodes', 'is_available')
    op.drop_column('movies', 'is_available')
    op.drop_column('tv_shows', 'is_available')


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse of upgrade(). is_available comes back defaulted to true; the
    # backfill from library_status is best-effort.
    op.add_column(
        'tv_shows',
        sa.Column(
            'is_available',
            sa.BOOLEAN(),
            server_default=sa.text('true'),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        'movies',
        sa.Column(
            'is_available',
            sa.BOOLEAN(),
            server_default=sa.text('true'),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        'episodes',
        sa.Column(
            'is_available',
            sa.BOOLEAN(),
            server_default=sa.text('true'),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.execute(sa.text("UPDATE movies SET is_available = (library_status = 'present')"))
    op.execute(
        sa.text("UPDATE tv_shows SET is_available = (library_status = 'present')")
    )
    op.execute(
        sa.text("UPDATE episodes SET is_available = (library_status = 'present')")
    )

    op.drop_index(
        'uix_user_episode',
        table_name='watch_progress',
        postgresql_where=sa.text('episode_id IS NOT NULL'),
    )
    op.drop_index(
        'uix_user_movie',
        table_name='watch_progress',
        postgresql_where=sa.text('movie_id IS NOT NULL'),
    )

    op.drop_constraint(
        'chk_watch_progress_catalog_target', 'watch_progress', type_='check'
    )

    op.add_column(
        'watch_progress',
        sa.Column(
            'media_file_id',
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        op.f('watch_progress_media_file_id_fkey'),
        'watch_progress',
        'media_files',
        ['media_file_id'],
        ['id'],
        ondelete='CASCADE',
    )

    op.create_check_constraint(
        'chk_watch_progress_catalog_target',
        'watch_progress',
        _OLD_CATALOG_TARGET_CHECK,
    )

    op.create_index(
        op.f('ix_watch_progress_user_movie'),
        'watch_progress',
        ['user_id', 'movie_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_watch_progress_user_episode'),
        'watch_progress',
        ['user_id', 'episode_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_watch_progress_media_file_id'),
        'watch_progress',
        ['media_file_id'],
        unique=False,
    )
    op.create_unique_constraint(
        op.f('uix_user_media_file'),
        'watch_progress',
        ['user_id', 'media_file_id'],
    )
