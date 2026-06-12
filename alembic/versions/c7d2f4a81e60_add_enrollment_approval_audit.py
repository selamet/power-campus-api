"""add enrollment approval audit

Revision ID: c7d2f4a81e60
Revises: b41e7c2d9a05
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2f4a81e60"
down_revision: Union[str, Sequence[str], None] = "b41e7c2d9a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("approvedBy", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("approvedAt", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_enrollments_approvedBy_users",
            "users",
            ["approvedBy"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_enrollments_approvedBy_users", type_="foreignkey")
        batch_op.drop_column("approvedAt")
        batch_op.drop_column("approvedBy")
