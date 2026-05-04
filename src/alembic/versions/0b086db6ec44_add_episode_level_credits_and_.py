"""add episode-level credits and department column

Revision ID: 0b086db6ec44
Revises: 02d1d2ef2524
Create Date: 2026-05-04 16:21:24.336463

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0b086db6ec44'
down_revision: Union[str, Sequence[str], None] = '02d1d2ef2524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. New episode FK + supporting partial index.
    op.add_column('credits', sa.Column('episode_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'credits_episode_id_fkey',
        'credits',
        'episodes',
        ['episode_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_credits_episode_order',
        'credits',
        ['episode_id', 'cast_order'],
        unique=False,
        postgresql_where=sa.text('episode_id IS NOT NULL'),
    )

    # 2. Replace the two-way CHECK with a three-way one. Alembic autogenerate
    # does not detect CHECK constraint changes, so this has to be explicit.
    op.drop_constraint('chk_credit_movie_or_show', 'credits', type_='check')
    op.create_check_constraint(
        'chk_credit_exactly_one_target',
        'credits',
        '(CASE WHEN movie_id IS NULL THEN 0 ELSE 1 END) + '
        '(CASE WHEN show_id IS NULL THEN 0 ELSE 1 END) + '
        '(CASE WHEN episode_id IS NULL THEN 0 ELSE 1 END) = 1',
    )

    # 3. department NOT NULL. Add with a server_default so any existing rows
    # backfill cleanly, then drop the default so the live schema matches the
    # model (which only declares a Python-side default).
    op.add_column(
        'credits',
        sa.Column(
            'department',
            sa.String(length=20),
            nullable=False,
            server_default='cast',
        ),
    )
    op.alter_column('credits', 'department', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('credits', 'department')

    op.drop_constraint('chk_credit_exactly_one_target', 'credits', type_='check')
    op.create_check_constraint(
        'chk_credit_movie_or_show',
        'credits',
        '(movie_id IS NULL AND show_id IS NOT NULL) OR '
        '(movie_id IS NOT NULL AND show_id IS NULL)',
    )

    op.drop_index(
        'ix_credits_episode_order',
        table_name='credits',
        postgresql_where=sa.text('episode_id IS NOT NULL'),
    )
    op.drop_constraint('credits_episode_id_fkey', 'credits', type_='foreignkey')
    op.drop_column('credits', 'episode_id')
