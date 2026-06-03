"""Invite model: a personalized self-service registration link for a student."""

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import AuditedBase


class InviteStatus(enum.StrEnum):
    """Lifecycle of an invite link."""

    pending = "pending"  # link issued, student has not submitted yet
    completed = "completed"  # student submitted the welcome form
    cancelled = "cancelled"


class Invite(AuditedBase):
    """A welcome-form link keyed by the student's national id (TCKN)."""

    __tablename__ = "invites"

    tckn: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Staff pre-selections that pre-fill the student's form.
    lang: Mapped[str] = mapped_column(String(64), nullable=False)
    course: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        Enum(
            InviteStatus,
            name="inviteStatus",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default=InviteStatus.pending.value,
        nullable=False,
    )
    # Set once the welcome form is submitted and a student record is created.
    student_id: Mapped[int | None] = mapped_column(
        "studentId", ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
