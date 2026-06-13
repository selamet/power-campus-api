"""add student passport number

Revision ID: a7e3c9f014b8
Revises: c3a8e1f50d62
Create Date: 2026-06-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7e3c9f014b8"
down_revision: Union[str, Sequence[str], None] = "c3a8e1f50d62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(sa.Column("passportNo", sa.String(length=32), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_students_passportNo"), ["passportNo"], unique=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_students_passportNo"))
        batch_op.drop_column("passportNo")
