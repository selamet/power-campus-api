"""Student management use cases."""

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.students.models import Enrollment, EnrollmentStatus, Student
from app.apps.students.repository import StudentRepository, provisional_code
from app.apps.students.schemas import NewStudentInput, StudentOut, StudentUpdate
from app.apps.users.models import User

# Fields whose Python names match their model attribute on each table.
_STUDENT_FIELDS = frozenset(
    {
        "name", "email", "phone", "tckn", "birth_date", "gender", "city", "address",
        "education_level", "school", "department", "grade",
        "contact_name", "contact_relation", "contact_phone",
    }
)
_ENROLLMENT_FIELDS = frozenset(
    {"lang", "level", "course", "plan", "status", "fee", "paid", "terms", "note"}
)


class StudentNotFoundError(Exception):
    """Raised when no student matches the given code."""


class PaymentPlanMissingError(Exception):
    """Raised when approving an enrollment that has no payment plan yet."""


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StudentRepository(session)

    async def list_students(
        self, *, limit: int | None = None, offset: int = 0
    ) -> list[StudentOut]:
        students = await self._repo.list_all(limit=limit, offset=offset)
        return [StudentOut.from_models(student) for student in students]

    async def create_student(self, payload: NewStudentInput) -> StudentOut:
        """Create a student together with their first enrollment."""
        student = Student(
            student_code=provisional_code(),
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            joined_at=payload.joined,
            source=payload.source,
        )
        student.enrollments.append(
            Enrollment(
                lang=payload.lang,
                level=payload.level,
                course=payload.course,
                plan=payload.plan,
                status=payload.status,
                fee=payload.fee,
                paid=payload.paid,
                next_payment_at=payload.next,
                start_at=payload.start,
                terms=payload.terms,
                note=payload.note,
            )
        )
        self._repo.add(student)
        await self._repo.assign_public_code(student)
        if payload.paid:
            # Keep the opening payment in the collection history so later
            # totals (which sum payment rows) include it.
            from app.apps.payments.models import Payment

            self._session.add(
                Payment(
                    enrollment_id=student.enrollments[-1].id,
                    amount=payload.paid,
                    paid_at=date.today(),
                    method=payload.pay_method or "Nakit",
                    note="Açılış tahsilatı",
                )
            )
        await self._session.commit()
        return StudentOut.from_models(student)

    async def update_student(self, code: str, payload: StudentUpdate) -> StudentOut:
        """Apply a partial update to a student and their current enrollment."""
        student = await self._get_or_404(code)
        enrollment = student.enrollments[-1]
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            if field in _STUDENT_FIELDS:
                setattr(student, field, value)
            elif field in _ENROLLMENT_FIELDS:
                setattr(enrollment, field, value)
            elif field == "next":
                enrollment.next_payment_at = value
            elif field == "start":
                enrollment.start_at = value
        await self._session.commit()
        return StudentOut.from_models(student)

    async def approve_student(self, code: str, approver: User) -> StudentOut:
        # Imported here to avoid a circular import with the payments service.
        from app.apps.payments.models import Payment
        from app.apps.payments.service import PaymentService

        student = await self._get_or_404(code)
        enrollment = student.enrollments[-1]
        # The fee (and with it the installment plan) must be agreed before the
        # enrollment can go active.
        if enrollment.fee <= 0:
            raise PaymentPlanMissingError(code)
        enrollment.status = EnrollmentStatus.active
        enrollment.approved_by = approver.id
        enrollment.approved_at = datetime.now(UTC)
        await PaymentService(self._session).ensure_schedule(enrollment)
        # An opening payment entered during approval should appear in the
        # collection history like one collected at manual registration.
        if enrollment.paid > 0:
            has_payments = await self._session.scalar(
                select(func.count()).select_from(Payment).where(
                    Payment.enrollment_id == enrollment.id
                )
            )
            if not has_payments:
                self._session.add(
                    Payment(
                        enrollment_id=enrollment.id,
                        amount=enrollment.paid,
                        paid_at=date.today(),
                        method="Nakit",
                        note="Açılış tahsilatı",
                    )
                )
        await self._session.commit()
        return StudentOut.from_models(student)

    async def reject_student(self, code: str) -> None:
        student = await self._get_or_404(code)
        await self._repo.delete(student)
        await self._session.commit()

    async def _get_or_404(self, code: str) -> Student:
        student = await self._repo.get_by_code(code)
        if student is None:
            raise StudentNotFoundError(code)
        return student
