"""Class API schemas."""

from datetime import date

from pydantic import Field

from app.apps.classes.lessons import LESSON_LABELS, LessonType
from app.apps.classes.models import ClassLesson, SchoolClass
from app.apps.classes.naming import class_display_name
from app.apps.students.models import EnrollmentStatus
from app.core.schemas import CamelModel


class ClassOut(CamelModel):
    """A class as returned to the frontend."""

    id: int
    term_id: int
    term_name: str
    level: str
    section: int
    # Display label, e.g. "A1/1".
    name: str
    student_count: int
    # Whether the class's term is the current one.
    current: bool
    teacher_id: int | None = None
    teacher_name: str | None = None

    @classmethod
    def from_model(
        cls, school_class: SchoolClass, *, student_count: int, today: date
    ) -> "ClassOut":
        term = school_class.term
        return cls(
            id=school_class.id,
            term_id=school_class.term_id,
            term_name=term.name if term else "",
            level=school_class.level,
            section=school_class.section,
            name=class_display_name(school_class.level, school_class.section),
            student_count=student_count,
            current=bool(term and term.start_date <= today <= term.end_date),
            teacher_id=school_class.teacher_id,
            teacher_name=school_class.teacher.name if school_class.teacher else None,
        )


class LessonInput(CamelModel):
    """Payload for creating a lesson on a class."""

    lesson_type: LessonType
    teacher_id: int | None = None
    session_duration_min: int = Field(ge=1)
    sessions_per_week: int = Field(ge=1)


class LessonUpdate(CamelModel):
    """Partial update of a lesson. ``teacher_id`` present-but-null clears it."""

    teacher_id: int | None = None
    session_duration_min: int | None = Field(default=None, ge=1)
    sessions_per_week: int | None = Field(default=None, ge=1)


class ClassLessonOut(CamelModel):
    """A class lesson as returned to the frontend."""

    id: int
    class_id: int
    lesson_type: LessonType
    lesson_type_label: str
    teacher_id: int | None
    teacher_name: str | None
    session_duration_min: int
    sessions_per_week: int
    weekly_total_min: int

    @classmethod
    def from_model(cls, lesson: ClassLesson) -> "ClassLessonOut":
        lt = LessonType(lesson.lesson_type)
        return cls(
            id=lesson.id,
            class_id=lesson.class_id,
            lesson_type=lt,
            lesson_type_label=LESSON_LABELS[lt],
            teacher_id=lesson.teacher_id,
            teacher_name=lesson.teacher.name if lesson.teacher else None,
            session_duration_min=lesson.session_duration_min,
            sessions_per_week=lesson.sessions_per_week,
            weekly_total_min=lesson.session_duration_min * lesson.sessions_per_week,
        )


class LessonTypeOut(CamelModel):
    """One entry of the fixed lesson-type catalog."""

    value: LessonType
    label: str
    default_sessions_per_week: int
    default_duration_min: int


class CreateClassRequest(CamelModel):
    """Payload for creating a class; section is auto-assigned when omitted."""

    term_id: int
    level: str
    section: int | None = Field(default=None, ge=1)
    # Omitted -> the four default lessons are seeded; a list -> exactly those.
    lessons: list[LessonInput] | None = None


class ClassUpdate(CamelModel):
    """Partial update of a class."""

    level: str | None = None
    section: int | None = Field(default=None, ge=1)
    teacher_id: int | None = None


class AssignStudentsRequest(CamelModel):
    """Assign existing term students to a class."""

    student_codes: list[str]


class ClassStudentOut(CamelModel):
    """A student in a class, as shown on the class roster."""

    student_id: str  # public student code, e.g. "PA-1042"
    name: str
    level: str
    status: EnrollmentStatus
