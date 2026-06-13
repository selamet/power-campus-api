"""Student API schemas.

The frontend treats a student as a single flat object that merges the person,
their course and its finance details. These schemas mirror that shape while the
database keeps ``students`` and ``enrollments`` separate.
"""

from datetime import date, datetime

from pydantic import EmailStr, Field

from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource
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
    # The term (semester) this enrollment belongs to, if assigned.
    term_id: int | None
    term_name: str | None
    # Extended profile, filled by the welcome or manual registration form.
    tckn: str | None
    # Passport number for foreign students; ``is_foreign`` is true when set.
    passport_no: str | None
    is_foreign: bool
    birth_date: date | None
    gender: str | None
    city: str | None
    address: str | None
    education_level: str | None
    school: str | None
    department: str | None
    grade: str | None
    contact_name: str | None
    contact_relation: str | None
    contact_phone: str | None
    # Approval audit (null while the enrollment is pending).
    approved_by_name: str | None
    approved_at: datetime | None

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
            term_id=enrollment.term_id,
            term_name=enrollment.term.name if enrollment.term else None,
            tckn=student.tckn,
            passport_no=student.passport_no,
            is_foreign=student.passport_no is not None,
            birth_date=student.birth_date,
            gender=student.gender,
            city=student.city,
            address=student.address,
            education_level=student.education_level,
            school=student.school,
            department=student.department,
            grade=student.grade,
            contact_name=student.contact_name,
            contact_relation=student.contact_relation,
            contact_phone=student.contact_phone,
            approved_by_name=enrollment.approver.full_name if enrollment.approver else None,
            approved_at=enrollment.approved_at,
        )


class EnrollmentOut(CamelModel):
    """A single enrollment (one term registration) of a student."""

    id: int
    term_id: int | None
    term_name: str | None
    lang: str
    level: str
    course: str
    plan: str
    status: EnrollmentStatus
    fee: int
    paid: int
    terms: int
    note: str | None
    start: date
    next: date | None
    approved_by_name: str | None
    approved_at: datetime | None

    @classmethod
    def from_model(cls, enrollment: Enrollment) -> "EnrollmentOut":
        return cls(
            id=enrollment.id,
            term_id=enrollment.term_id,
            term_name=enrollment.term.name if enrollment.term else None,
            lang=enrollment.lang,
            level=enrollment.level,
            course=enrollment.course,
            plan=enrollment.plan,
            status=enrollment.status,
            fee=enrollment.fee,
            paid=enrollment.paid,
            terms=enrollment.terms,
            note=enrollment.note,
            start=enrollment.start_at,
            next=enrollment.next_payment_at,
            approved_by_name=enrollment.approver.full_name if enrollment.approver else None,
            approved_at=enrollment.approved_at,
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
    passport_no: str | None = None
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
    term_id: int | None = None


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
    # Turkish students are keyed by TCKN; foreign students by passport number.
    tckn: str | None = None
    passport_no: str | None = None
    source: StudentSource | None = StudentSource.manual
    terms: int = Field(default=1, ge=1)
    note: str | None = None
    # Method of the opening payment, when one was collected at registration.
    pay_method: str | None = None


class NewEnrollmentInput(CamelModel):
    """Payload for enrolling an existing student into another term.

    Mirrors the course/finance subset of `NewStudentInput`; no person fields,
    since the student already exists (identified by their unique TCKN/code).
    """

    term_id: int | None = None
    lang: str
    level: str
    course: str
    status: EnrollmentStatus = EnrollmentStatus.active
    plan: str
    fee: int = Field(ge=0)
    paid: int = Field(default=0, ge=0)
    next: date | None = None
    start: date
    terms: int = Field(default=1, ge=1)
    note: str | None = None
    pay_method: str | None = None
