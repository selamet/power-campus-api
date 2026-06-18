"""Class (section) model: a level-based group of students within a term."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import AuditedBase

if TYPE_CHECKING:
    from app.apps.teachers.models import Teacher
    from app.apps.terms.models import Term


class SchoolClass(AuditedBase):
    """A section (e.g. ``A1/1``) students are grouped into for a term.

    A class is identified by its level and a section number, scoped to a term.
    Membership lives on :class:`Enrollment` (``classId``), so a student belongs
    to at most one class per term. There is no capacity limit.
    """

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("termId", "level", "section", name="uq_classes_term_level_section"),
    )

    term_id: Mapped[int] = mapped_column(
        "termId",
        ForeignKey("terms.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # The level the class teaches, stored as the full option label (e.g.
    # "A1 — Başlangıç"); the display code ("A1") is derived for the UI.
    level: Mapped[str] = mapped_column(String(64), nullable=False)
    # Section number within the term+level, so "A1/1", "A1/2", …
    section: Mapped[int] = mapped_column(Integer, nullable=False)

    term: Mapped["Term"] = relationship("Term", lazy="selectin")

    teacher_id: Mapped[int | None] = mapped_column(
        "teacherId",
        ForeignKey("teachers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    teacher: Mapped["Teacher | None"] = relationship(
        "Teacher", lazy="selectin", back_populates="classes"
    )

    lessons: Mapped[list["ClassLesson"]] = relationship(
        "ClassLesson",
        back_populates="school_class",
        cascade="all, delete-orphan",
        order_by="ClassLesson.id",
    )


class ClassLesson(AuditedBase):
    """A lesson within a class: a type, weekly session count, duration and an
    optional teacher. A class seeds four by default; rows are freely added or
    hard-deleted. Same type may repeat — there is no unique constraint."""

    __tablename__ = "class_lessons"

    class_id: Mapped[int] = mapped_column(
        "classId",
        ForeignKey("classes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Stores a LessonType value (e.g. "speaking"); see app.apps.classes.lessons.
    lesson_type: Mapped[str] = mapped_column("lessonType", String(32), nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(
        "teacherId",
        ForeignKey("teachers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    session_duration_min: Mapped[int] = mapped_column(
        "sessionDurationMin", Integer, nullable=False
    )
    sessions_per_week: Mapped[int] = mapped_column(
        "sessionsPerWeek", Integer, nullable=False
    )

    teacher: Mapped["Teacher | None"] = relationship("Teacher", lazy="selectin")
    school_class: Mapped["SchoolClass"] = relationship(
        "SchoolClass", back_populates="lessons"
    )
