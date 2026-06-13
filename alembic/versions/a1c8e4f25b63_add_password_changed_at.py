"""add password changed at

Revision ID: a1c8e4f25b63
Revises: f4b1d6c2a907
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c8e4f25b63"
down_revision: Union[str, Sequence[str], None] = "f4b1d6c2a907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("passwordChangedAt", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("passwordChangedAt")
