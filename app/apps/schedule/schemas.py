"""Schedule API schemas."""

from datetime import time
from typing import Any

from pydantic import Field

from app.apps.classes.lessons import LessonType
from app.core.schemas import CamelModel


class TermSettingsUpdate(CamelModel):
    working_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    day_start: time = time(9)
    day_end: time = time(18)
    default_duration: int = Field(default=45, ge=1)
    default_per_day: int = Field(default=3, ge=1)
    break_min: int = Field(default=0, ge=0)
    teacher_rules: dict[str, Any] = Field(default_factory=dict)


class TermSettingsOut(CamelModel):
    term_id: int
    working_days: list[int]
    day_start: time
    day_end: time
    default_duration: int
    default_per_day: int
    break_min: int
    teacher_rules: dict[str, Any]


class ScheduleConfigUpdate(CamelModel):
    rules: dict[str, Any] = Field(default_factory=dict)


class ScheduleConfigOut(CamelModel):
    class_id: int
    rules: dict[str, Any]


class SessionOut(CamelModel):
    id: int
    class_lesson_id: int
    class_id: int
    class_name: str
    lesson_type: LessonType
    teacher_id: int | None
    teacher_name: str | None
    weekday: int
    start_time: time
    end_time: time


class SessionPreview(CamelModel):
    class_lesson_id: int
    class_id: int
    lesson_type: LessonType
    teacher_id: int | None
    teacher_name: str | None
    weekday: int
    start_time: time
    end_time: time


class ReportItem(CamelModel):
    class_id: int
    lesson_type: LessonType
    reason: str


class GeneratePreview(CamelModel):
    sessions: list[SessionPreview]
    report: list[ReportItem]
