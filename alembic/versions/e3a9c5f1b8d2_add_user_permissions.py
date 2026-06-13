"""add user permissions

Revision ID: e3a9c5f1b8d2
Revises: c7d2f4a81e60
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3a9c5f1b8d2"
down_revision: Union[str, Sequence[str], None] = "c7d2f4a81e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "userPermissions",
        sa.Column("userId", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["userId"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("userId", "permission"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("userPermissions")
