"""Student management use cases."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.students.models import Enrollment, EnrollmentStatus, Student
from app.apps.students.repository import StudentRepository
from app.apps.students.schemas import NewStudentInput, StudentOut, StudentUpdate

# Fields whose Python names match their model attribute on each table.
_STUDENT_FIELDS = frozenset(
    {
        "name", "email", "phone", "tckn", "birth_date", "gender", "city", "address",
        "education_level", "school", "department", "grade",
        "contact_name", "contact_relation", "contact_phone",
    }
)
_ENROLLMENT_FIELDS = frozenset({"lang", "level", "course", "plan", "status", "fee", "paid"})


class StudentNotFoundError(Exception):
    """Raised when no student matches the given code."""


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StudentRepository(session)

    async def list_students(self) -> list[StudentOut]:
        students = await self._repo.list_all()
        return [StudentOut.from_models(student) for student in students]

    async def create_student(self, payload: NewStudentInput) -> StudentOut:
        """Create a student together with their first enrollment."""
        student = Student(
            student_code=await self._repo.next_student_code(),
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
            )
        )
        self._repo.add(student)
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

    async def approve_student(self, code: str) -> StudentOut:
        # Imported here to avoid a circular import with the payments service.
        from app.apps.payments.service import PaymentService

        student = await self._get_or_404(code)
        enrollment = student.enrollments[-1]
        enrollment.status = EnrollmentStatus.active
        await PaymentService(self._session).ensure_schedule(enrollment)
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
