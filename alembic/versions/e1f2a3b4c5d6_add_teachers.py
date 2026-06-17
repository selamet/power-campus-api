"""add teachers

Revision ID: e1f2a3b4c5d6
Revises: d9c2b7e34a15
Create Date: 2026-06-18 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d9c2b7e34a15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teachers",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("languages", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("levels", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("userId", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("createdBy", sa.Integer(), nullable=True),
        sa.Column("updatedAt", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updatedBy", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["userId"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_teachers_email"), ["email"], unique=True)

    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("teacherId", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_classes_teacherId"), ["teacherId"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_classes_teacherId_teachers"), "teachers", ["teacherId"], ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_classes_teacherId_teachers"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_classes_teacherId"))
        batch_op.drop_column("teacherId")
    with op.batch_alter_table("teachers", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_teachers_email"))
    op.drop_table("teachers")
