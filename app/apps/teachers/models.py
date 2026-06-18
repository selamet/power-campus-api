"""Teacher entity: a standalone person who can be assigned to classes."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import AuditedBase

if TYPE_CHECKING:
    from app.apps.classes.models import SchoolClass


class TeacherStatus(enum.StrEnum):
    """Whether a teacher is currently teaching."""

    active = "active"
    inactive = "inactive"


class Teacher(AuditedBase):
    """A teacher at the academy. Not a login account (see ``user_id``)."""

    __tablename__ = "teachers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[TeacherStatus] = mapped_column(
        Enum(
            TeacherStatus,
            name="teacherStatus",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default=TeacherStatus.active.value,
        nullable=False,
    )
    # Teaching profile: which languages and CEFR levels the teacher can teach.
    languages: Mapped[list[str]] = mapped_column(
        JSON, server_default="[]", nullable=False, default=list
    )
    levels: Mapped[list[str]] = mapped_column(
        JSON, server_default="[]", nullable=False, default=list
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Reserved for a future teacher login; unused for now (mirrors Student.user_id).
    user_id: Mapped[int | None] = mapped_column(
        "userId", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="teacher")
