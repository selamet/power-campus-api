"""add class_lessons

Revision ID: f5a2c9d3b1e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-18 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f5a2c9d3b1e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "class_lessons",
        sa.Column("classId", sa.Integer(), nullable=False),
        sa.Column("lessonType", sa.String(length=32), nullable=False),
        sa.Column("teacherId", sa.Integer(), nullable=True),
        sa.Column("sessionDurationMin", sa.Integer(), nullable=False),
        sa.Column("sessionsPerWeek", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("createdBy", sa.Integer(), nullable=True),
        sa.Column("updatedAt", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updatedBy", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["classId"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacherId"], ["teachers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("class_lessons", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_class_lessons_classId"), ["classId"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_class_lessons_teacherId"), ["teacherId"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("class_lessons", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_class_lessons_teacherId"))
        batch_op.drop_index(batch_op.f("ix_class_lessons_classId"))
    op.drop_table("class_lessons")
