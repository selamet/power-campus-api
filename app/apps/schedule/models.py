"""Schedule models: settings, builder config, and placed sessions."""

from datetime import time
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, SmallInteger, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import AuditedBase

if TYPE_CHECKING:
    from app.apps.classes.models import ClassLesson


class TermScheduleSettings(AuditedBase):
    """Per-term defaults that frame the weekly grid."""

    __tablename__ = "term_schedule_settings"
    __table_args__ = (UniqueConstraint("termId", name="uq_term_schedule_settings_termId"),)

    term_id: Mapped[int] = mapped_column(
        "termId", ForeignKey("terms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    working_days: Mapped[list[int]] = mapped_column(
        "workingDays", JSON, default=list, nullable=False
    )
    day_start: Mapped[time] = mapped_column("dayStart", Time, nullable=False)
    day_end: Mapped[time] = mapped_column("dayEnd", Time, nullable=False)
    default_duration: Mapped[int] = mapped_column(
        "defaultDuration", SmallInteger, nullable=False
    )
    default_per_day: Mapped[int] = mapped_column(
        "defaultPerDay", SmallInteger, nullable=False
    )
    break_min: Mapped[int] = mapped_column("breakMin", SmallInteger, nullable=False, default=0)
    teacher_rules: Mapped[dict[str, Any]] = mapped_column(
        "teacherRules", JSON, default=dict, nullable=False
    )
    day_windows: Mapped[dict[str, Any]] = mapped_column(
        "dayWindows", JSON, default=dict, nullable=False
    )


class ScheduleConfig(AuditedBase):
    """Builder rule-set for a class (generator input)."""

    __tablename__ = "schedule_configs"
    __table_args__ = (UniqueConstraint("classId", name="uq_schedule_configs_classId"),)

    class_id: Mapped[int] = mapped_column(
        "classId", ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ScheduleSession(AuditedBase):
    """A single placed weekly session (generator output / real timetable)."""

    __tablename__ = "schedule_sessions"

    class_lesson_id: Mapped[int] = mapped_column(
        "classLessonId",
        ForeignKey("class_lessons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon..6=Sun
    start_time: Mapped[time] = mapped_column("startTime", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("endTime", Time, nullable=False)
    locked: Mapped[bool] = mapped_column("locked", Boolean, default=False, nullable=False)

    class_lesson: Mapped["ClassLesson"] = relationship("ClassLesson", lazy="selectin")
