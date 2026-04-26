"""add library_status to catalog

Revision ID: 0f8c596bdb1e
Revises: aad116581d78
Create Date: 2026-04-26 17:42:52.618563

Adds a stored `library_status` column on the catalog tables. Values:
  - 'present'     : at least one playable file is available
  - 'removed'     : used to be in library, file gone, watch state preserved
  - 'placeholder' : TMDB-known but no file yet (reserved for partial seasons)

Backfilled from the existing `is_available` boolean. Seasons have no
is_available column today, so they backfill from whether any child episode
is available.

`is_available` is intentionally LEFT IN PLACE during this migration; a later
revision will drop it once readers have migrated to library_status.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0f8c596bdb1e'
down_revision: Union[str, Sequence[str], None] = 'aad116581d78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUS_CHECK = "library_status IN ('present', 'removed', 'placeholder')"


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add the column nullable on every catalog table so the backfill UPDATE
    #    has somewhere to write before we tighten the constraint.
    op.add_column(
        'movies', sa.Column('library_status', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'tv_shows', sa.Column('library_status', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'seasons', sa.Column('library_status', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'episodes', sa.Column('library_status', sa.String(length=20), nullable=True)
    )

    # 2. Backfill from is_available where the column exists.
    for table in ('movies', 'tv_shows', 'episodes'):
        op.execute(
            sa.text(
                f"""
            UPDATE {table}
            SET library_status = CASE
                WHEN is_available THEN 'present'
                ELSE 'removed'
            END
            """
            )
        )

    # Seasons have no is_available, derive from child episodes.
    op.execute(
        sa.text(
            """
        UPDATE seasons
        SET library_status = CASE
            WHEN EXISTS (
                SELECT 1 FROM episodes
                WHERE episodes.season_id = seasons.id
                  AND episodes.is_available
            ) THEN 'present'
            ELSE 'removed'
        END
        """
        )
    )

    # 3. Lock down: NOT NULL + default + CHECK on each table.
    for table, check_name in (
        ('movies', 'chk_movies_library_status'),
        ('tv_shows', 'chk_tv_shows_library_status'),
        ('seasons', 'chk_seasons_library_status'),
        ('episodes', 'chk_episodes_library_status'),
    ):
        op.alter_column(
            table, 'library_status', nullable=False, server_default='present'
        )
        op.create_check_constraint(check_name, table, _STATUS_CHECK)

    # 4. Indexes that drive read-path filters and rollup EXISTS queries.
    op.create_index(
        'ix_episodes_season_status',
        'episodes',
        ['season_id', 'library_status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_movies_library_status'), 'movies', ['library_status'], unique=False
    )
    op.create_index(
        'ix_seasons_show_status', 'seasons', ['show_id', 'library_status'], unique=False
    )
    op.create_index(
        op.f('ix_tv_shows_library_status'), 'tv_shows', ['library_status'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tv_shows_library_status'), table_name='tv_shows')
    op.drop_index('ix_seasons_show_status', table_name='seasons')
    op.drop_index(op.f('ix_movies_library_status'), table_name='movies')
    op.drop_index('ix_episodes_season_status', table_name='episodes')

    for table, check_name in (
        ('episodes', 'chk_episodes_library_status'),
        ('seasons', 'chk_seasons_library_status'),
        ('tv_shows', 'chk_tv_shows_library_status'),
        ('movies', 'chk_movies_library_status'),
    ):
        op.drop_constraint(check_name, table, type_='check')
        op.drop_column(table, 'library_status')
