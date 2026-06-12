"""add enrollment terms and note

Revision ID: b41e7c2d9a05
Revises: 2fca8a8e6646
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b41e7c2d9a05"
down_revision: Union[str, Sequence[str], None] = "2fca8a8e6646"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("terms", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(sa.Column("note", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.drop_column("note")
        batch_op.drop_column("terms")
