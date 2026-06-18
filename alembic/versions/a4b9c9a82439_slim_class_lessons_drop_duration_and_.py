"""slim class_lessons: drop duration and weekly count

Revision ID: a4b9c9a82439
Revises: f5a2c9d3b1e7
Create Date: 2026-06-19 01:34:27.885665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b9c9a82439'
down_revision: Union[str, Sequence[str], None] = 'f5a2c9d3b1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop sessionDurationMin and sessionsPerWeek from class_lessons."""
    with op.batch_alter_table('class_lessons', schema=None) as batch_op:
        batch_op.drop_column('sessionsPerWeek')
        batch_op.drop_column('sessionDurationMin')


def downgrade() -> None:
    """Restore sessionDurationMin and sessionsPerWeek to class_lessons."""
    with op.batch_alter_table('class_lessons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sessionDurationMin', sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column('sessionsPerWeek', sa.INTEGER(), nullable=False))
