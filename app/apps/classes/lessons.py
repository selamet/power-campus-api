"""Fixed lesson-type catalog: the four lessons a class can have.

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

# Default session duration (minutes); owned here for reference by the schedule module.
DEFAULT_SESSION_DURATION_MIN = 45
