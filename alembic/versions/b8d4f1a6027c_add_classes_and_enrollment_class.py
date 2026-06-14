"""add classes and enrollment class link

Revision ID: b8d4f1a6027c
Revises: a7e3c9f014b8
Create Date: 2026-06-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8d4f1a6027c"
down_revision: Union[str, Sequence[str], None] = "a7e3c9f014b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "classes",
        sa.Column("termId", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=64), nullable=False),
        sa.Column("section", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["termId"], ["terms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["createdBy"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updatedBy"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("termId", "level", "section", name="uq_classes_term_level_section"),
    )
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_classes_termId"), ["termId"], unique=False)

    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("classId", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_enrollments_classId"), ["classId"], unique=False)
        batch_op.create_foreign_key(
            batch_op.f("fk_enrollments_classId_classes"),
            "classes",
            ["classId"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("enrollments", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_enrollments_classId_classes"), type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_enrollments_classId"))
        batch_op.drop_column("classId")

    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_classes_termId"))

    op.drop_table("classes")
