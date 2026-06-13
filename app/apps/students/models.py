"""Student (person) and Enrollment (course registration + finance) models."""

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import AuditedBase

if TYPE_CHECKING:
    from app.apps.terms.models import Term
    from app.apps.users.models import User


class StudentSource(enum.StrEnum):
    """How the student record entered the system."""

    invite = "davet"
    manual = "manuel"


class EnrollmentStatus(enum.StrEnum):
    """Lifecycle of a course registration."""

    active = "active"
    pending = "pending"
    inactive = "inactive"


class Student(AuditedBase):
    """A person enrolled (or invited to enroll) at the academy."""

    __tablename__ = "students"

    # Public, human-readable identifier exposed by the API (e.g. "PA-1042").
    student_code: Mapped[str] = mapped_column(
        "studentCode", String(16), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    joined_at: Mapped[date] = mapped_column("joinedAt", Date, nullable=False)

    # Extended profile, collected by the manual and self-service (welcome)
    # registration forms. All optional so existing records stay valid.
    # ``tckn`` is the public identifier the panel addresses a student by, so it
    # is uniquely indexed; the nullable column still allows many records without
    # one (manual entries), since a unique index permits multiple NULLs.
    tckn: Mapped[str | None] = mapped_column(
        String(11), unique=True, index=True, nullable=True
    )
    birth_date: Mapped[date | None] = mapped_column("birthDate", Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_level: Mapped[str | None] = mapped_column("educationLevel", String(32), nullable=True)
    school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column("contactName", String(255), nullable=True)
    contact_relation: Mapped[str | None] = mapped_column(
        "contactRelation", String(32), nullable=True
    )
    contact_phone: Mapped[str | None] = mapped_column("contactPhone", String(32), nullable=True)

    source: Mapped[StudentSource | None] = mapped_column(
        Enum(
            StudentSource,
            name="studentSource",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    # Reserved for a future student login; unused while students don't sign in.
    user_id: Mapped[int | None] = mapped_column(
        "userId", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="Enrollment.id",
    )


class Enrollment(AuditedBase):
    """A student's registration to a course, including its finance details."""

    __tablename__ = "enrollments"

    student_id: Mapped[int] = mapped_column(
        "studentId",
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # The term this registration belongs to; chosen at approval, optional so
    # legacy and not-yet-approved enrollments stay valid.
    term_id: Mapped[int | None] = mapped_column(
        "termId", ForeignKey("terms.id", ondelete="SET NULL"), index=True, nullable=True
    )
    lang: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False)
    course: Mapped[str] = mapped_column(String(64), nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(
            EnrollmentStatus,
            name="enrollmentStatus",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Money is stored as whole Turkish Lira (₺), integer, no sub-units (kuruş).
    fee: Mapped[int] = mapped_column(Integer, nullable=False)
    paid: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    next_payment_at: Mapped[date | None] = mapped_column("nextPaymentAt", Date, nullable=True)
    start_at: Mapped[date] = mapped_column("startAt", Date, nullable=False)
    # Number of course terms ("kur") the student signed up for.
    terms: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    # Free-form finance note entered by staff during registration.
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Who approved the enrollment and when (null while pending).
    approved_by: Mapped[int | None] = mapped_column(
        "approvedBy", ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        "approvedAt", DateTime(timezone=True), nullable=True
    )
    approver: Mapped["User | None"] = relationship(
        "User", lazy="selectin", foreign_keys=[approved_by]
    )
    term: Mapped["Term | None"] = relationship("Term", lazy="selectin")

    student: Mapped["Student"] = relationship(back_populates="enrollments")
