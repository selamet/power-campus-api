"""Class API schemas."""

from datetime import date

from pydantic import Field

from app.apps.classes.models import SchoolClass
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


class CreateClassRequest(CamelModel):
    """Payload for creating a class; section is auto-assigned when omitted."""

    term_id: int
    level: str
    section: int | None = Field(default=None, ge=1)


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
