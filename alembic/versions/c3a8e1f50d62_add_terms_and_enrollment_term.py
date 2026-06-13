"""add terms and enrollment term link

Revision ID: c3a8e1f50d62
Revises: b2f7a3c1d9e4
Create Date: 2026-06-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3a8e1f50d62"
down_revision: Union[str, Sequence[str], None] = "b2f7a3c1d9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "terms",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("startDate", sa.Date(), nullable=False),
        sa.Column("endDate", sa.Date(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("createdBy", sa.Integer(), nullable=True),
        sa.Column(
            "updatedAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updatedBy", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("termId", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_enrollments_termId"), ["termId"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_enrollments_termId_terms"),
            "terms",
            ["termId"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_enrollments_termId_terms"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_enrollments_termId"))
        batch_op.drop_column("termId")

    op.drop_table("terms")
