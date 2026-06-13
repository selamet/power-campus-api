"""add unique index on student tckn

Revision ID: b2f7a3c1d9e4
Revises: a1c8e4f25b63
Create Date: 2026-06-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2f7a3c1d9e4"
down_revision: Union[str, Sequence[str], None] = "a1c8e4f25b63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # TCKN becomes the public identifier the panel addresses a student by. A
    # unique index keeps non-null values distinct while still permitting many
    # records without one (manual entries stay NULL).
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_students_tckn"), ["tckn"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_students_tckn"))
