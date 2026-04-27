"""decouple watch_progress from media_files

Revision ID: de12da6d2329
Revises: 0f8c596bdb1e
Create Date: 2026-04-26 19:34:18.832890

Adds catalog-side anchors (movie_id, episode_id) to watch_progress so a row
can survive deletion of its MediaFile. Backfilled from the existing FK chain
through media_files. media_file_id is INTENTIONALLY KEPT during this
migration; PR 3 will switch reads off it and drop the column.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = 'de12da6d2329'
down_revision: Union[str, Sequence[str], None] = '0f8c596bdb1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CATALOG_TARGET_CHECK = (
    '(movie_id IS NULL AND episode_id IS NOT NULL) OR '
    '(movie_id IS NOT NULL AND episode_id IS NULL) OR '
    '(movie_id IS NULL AND episode_id IS NULL)'
)


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add nullable columns + their FKs.
    op.add_column('watch_progress', sa.Column('movie_id', sa.Integer(), nullable=True))
    op.add_column('watch_progress', sa.Column('episode_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_watch_progress_movie_id_movies',
        'watch_progress', 'movies', ['movie_id'], ['id'], ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_watch_progress_episode_id_episodes',
        'watch_progress', 'episodes', ['episode_id'], ['id'], ondelete='CASCADE',
    )

    # 2. Backfill: each existing row's parent MediaFile points at exactly one
    #    of (movie_id, episode_id); copy that side to the watch_progress row.
    op.execute(sa.text(
        """
        UPDATE watch_progress AS wp
        SET movie_id = mf.movie_id,
            episode_id = mf.episode_id
        FROM media_files AS mf
        WHERE wp.media_file_id = mf.id
        """
    ))

    # 3. Catalog-target CHECK. NULL/NULL is allowed during the dual-write
    #    window because the FK from media_files might be gone before the
    #    catalog target is set; PR 3 tightens this once media_file_id drops.
    op.create_check_constraint(
        'chk_watch_progress_catalog_target',
        'watch_progress',
        _CATALOG_TARGET_CHECK,
    )

    # 4. Indexes (single-column for FK lookups, composite for future read path).
    op.create_index(op.f('ix_watch_progress_episode_id'), 'watch_progress', ['episode_id'], unique=False)
    op.create_index(op.f('ix_watch_progress_movie_id'), 'watch_progress', ['movie_id'], unique=False)
    op.create_index('ix_watch_progress_user_episode', 'watch_progress', ['user_id', 'episode_id'], unique=False)
    op.create_index('ix_watch_progress_user_movie', 'watch_progress', ['user_id', 'movie_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_watch_progress_user_movie', table_name='watch_progress')
    op.drop_index('ix_watch_progress_user_episode', table_name='watch_progress')
    op.drop_index(op.f('ix_watch_progress_movie_id'), table_name='watch_progress')
    op.drop_index(op.f('ix_watch_progress_episode_id'), table_name='watch_progress')
    op.drop_constraint('chk_watch_progress_catalog_target', 'watch_progress', type_='check')
    op.drop_constraint('fk_watch_progress_episode_id_episodes', 'watch_progress', type_='foreignkey')
    op.drop_constraint('fk_watch_progress_movie_id_movies', 'watch_progress', type_='foreignkey')
    op.drop_column('watch_progress', 'episode_id')
    op.drop_column('watch_progress', 'movie_id')
