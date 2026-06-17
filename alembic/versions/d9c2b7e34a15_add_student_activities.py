"""add student activities

Revision ID: d9c2b7e34a15
Revises: b8d4f1a6027c
Create Date: 2026-06-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9c2b7e34a15"
down_revision: Union[str, Sequence[str], None] = "b8d4f1a6027c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "student_activities",
        sa.Column("studentId", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["studentId"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("student_activities", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_student_activities_studentId"), ["studentId"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("student_activities", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_student_activities_studentId"))
    op.drop_table("student_activities")
