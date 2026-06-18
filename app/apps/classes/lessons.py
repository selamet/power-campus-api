"""Fixed lesson-type catalog: the four lessons a class can have and their defaults.

Lesson types are a closed set defined here in code (no lookup table), mirroring
how levels/courses/plans are plain values elsewhere.
"""

import enum


class LessonType(enum.StrEnum):
    """The fixed set of lessons a class can offer."""

    speaking = "speaking"
    reading = "reading"
    writing = "writing"
    speaking_club = "speaking_club"


LESSON_LABELS: dict[LessonType, str] = {
    LessonType.speaking: "Speaking",
    LessonType.reading: "Reading",
    LessonType.writing: "Writing",
    LessonType.speaking_club: "Speaking Club",
}

# Default weekly session count per lesson type.
DEFAULT_SESSIONS_PER_WEEK: dict[LessonType, int] = {
    LessonType.speaking: 1,
    LessonType.reading: 3,
    LessonType.writing: 3,
    LessonType.speaking_club: 3,
}

# Shared default session duration (minutes) for every lesson.
DEFAULT_SESSION_DURATION_MIN = 60


def default_lessons() -> list[tuple[LessonType, int, int]]:
    """``(lesson_type, sessions_per_week, duration_min)`` for all four lessons,
    in catalog order — used to seed a new class."""
    return [
        (lesson_type, DEFAULT_SESSIONS_PER_WEEK[lesson_type], DEFAULT_SESSION_DURATION_MIN)
        for lesson_type in LessonType
    ]
