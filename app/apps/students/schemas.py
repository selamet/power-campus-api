"""Student API schemas.

The frontend treats a student as a single flat object that merges the person,
their course and its finance details. These schemas mirror that shape while the
database keeps ``students`` and ``enrollments`` separate.
"""

from datetime import date

from pydantic import EmailStr, Field

from app.apps.students.models import EnrollmentStatus, Student, StudentSource
from app.core.schemas import CamelModel


class StudentOut(CamelModel):
    """Combined student + enrollment view returned to the frontend."""

    id: str  # public student code, e.g. "PA-1042"
    name: str
    lang: str
    level: str
    course: str
    status: EnrollmentStatus
    phone: str
    start: date
    fee: int
    paid: int
    plan: str
    next: date | None
    joined: date
    email: EmailStr
    source: StudentSource | None
    terms: int
    note: str | None

    @classmethod
    def from_models(cls, student: Student) -> "StudentOut":
        """Build the flat view from a student and its current enrollment."""
        enrollment = student.enrollments[-1]
        return cls(
            id=student.student_code,
            name=student.name,
            lang=enrollment.lang,
            level=enrollment.level,
            course=enrollment.course,
            status=enrollment.status,
            phone=student.phone,
            start=enrollment.start_at,
            fee=enrollment.fee,
            paid=enrollment.paid,
            plan=enrollment.plan,
            next=enrollment.next_payment_at,
            joined=student.joined_at,
            email=student.email,
            source=student.source,
            terms=enrollment.terms,
            note=enrollment.note,
        )


class StudentUpdate(CamelModel):
    """Partial update of a student and their current enrollment.

    Only the fields present in the request are applied (``exclude_unset``).
    """

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    lang: str | None = None
    level: str | None = None
    course: str | None = None
    plan: str | None = None
    status: EnrollmentStatus | None = None
    fee: int | None = Field(default=None, ge=0)
    paid: int | None = Field(default=None, ge=0)
    next: date | None = None
    start: date | None = None
    tckn: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    city: str | None = None
    address: str | None = None
    education_level: str | None = None
    school: str | None = None
    department: str | None = None
    grade: str | None = None
    contact_name: str | None = None
    contact_relation: str | None = None
    contact_phone: str | None = None
    terms: int | None = Field(default=None, ge=1)
    note: str | None = None


class NewStudentInput(CamelModel):
    """Payload for manually creating a student (mirrors `NewStudentInput`)."""

    name: str
    lang: str
    level: str
    course: str
    status: EnrollmentStatus = EnrollmentStatus.active
    phone: str
    start: date
    fee: int = Field(ge=0)
    paid: int = Field(default=0, ge=0)
    plan: str
    next: date | None = None
    joined: date
    email: EmailStr
    source: StudentSource | None = StudentSource.manual
    terms: int = Field(default=1, ge=1)
    note: str | None = None
    # Method of the opening payment, when one was collected at registration.
    pay_method: str | None = None
