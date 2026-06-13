"""Term management use cases."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.students.models import Enrollment, EnrollmentStatus, Student
from app.apps.terms.models import Term
from app.apps.terms.naming import playful_name
from app.apps.terms.repository import TermRepository
from app.apps.terms.schemas import (
    BulkEnrollRequest,
    CreateTermRequest,
    TermOut,
    TermStudentOut,
    TermUpdate,
)
from app.apps.users.models import User


class TermNotFoundError(Exception):
    """Raised when no term matches the given id."""


class InvalidTermDatesError(Exception):
    """Raised when a term would end before it starts."""

    message = "Dönem bitiş tarihi başlangıçtan önce olamaz."


class TermService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TermRepository(session)

    async def list_terms(self) -> list[TermOut]:
        today = date.today()
        return [TermOut.from_model(term, today=today) for term in await self._repo.list_all()]

    async def create_term(self, payload: CreateTermRequest) -> TermOut:
        if payload.end < payload.start:
            raise InvalidTermDatesError
        name = (payload.name or "").strip() or playful_name(payload.start.year)
        term = Term(name=name, start_date=payload.start, end_date=payload.end)
        self._repo.add(term)
        await self._session.commit()
        return TermOut.from_model(term, today=date.today())

    async def update_term(self, term_id: int, payload: TermUpdate) -> TermOut:
        term = await self._repo.get_by_id(term_id)
        if term is None:
            raise TermNotFoundError(term_id)
        data = payload.model_dump(exclude_unset=True)
        name = data.get("name")
        if name is not None and name.strip():
            term.name = name.strip()
        if data.get("start") is not None:
            term.start_date = data["start"]
        if data.get("end") is not None:
            term.end_date = data["end"]
        if term.end_date < term.start_date:
            raise InvalidTermDatesError
        await self._session.commit()
        return TermOut.from_model(term, today=date.today())

    async def list_term_students(self, term_id: int) -> list[TermStudentOut]:
        """The students enrolled in a term, by name."""
        rows = await self._session.execute(
            select(Enrollment, Student)
            .join(Student, Enrollment.student_id == Student.id)
            .where(Enrollment.term_id == term_id)
            .order_by(Student.name)
        )
        return [
            TermStudentOut(
                student_id=student.student_code,
                name=student.name,
                lang=enrollment.lang,
                level=enrollment.level,
                course=enrollment.course,
                status=enrollment.status,
                fee=enrollment.fee,
                paid=enrollment.paid,
            )
            for enrollment, student in rows
        ]

    async def bulk_enroll(
        self, term_id: int, payload: BulkEnrollRequest, actor: User
    ) -> list[TermStudentOut]:
        """Enroll the given existing students into a term as active enrollments.

        This simply registers each student in the term. No fee, payment plan or
        payment record is created here; finance is handled separately on the
        student's enrollment. Students already registered in this term are
        skipped, so re-running is safe (no duplicate enrollments).
        """
        term = await self._repo.get_by_id(term_id)
        if term is None:
            raise TermNotFoundError(term_id)
        students = list(
            await self._session.scalars(
                select(Student)
                .where(Student.student_code.in_(payload.student_codes))
                .options(selectinload(Student.enrollments))
            )
        )
        for student in students:
            if any(enrollment.term_id == term_id for enrollment in student.enrollments):
                continue
            enrollment = Enrollment(
                lang="",
                level="",
                course="",
                plan="",
                status=EnrollmentStatus.active,
                fee=0,
                paid=0,
                start_at=term.start_date,
            )
            enrollment.term = term
            enrollment.approver = actor
            enrollment.approved_at = datetime.now(UTC)
            student.enrollments.append(enrollment)

        await self._session.commit()
        return await self.list_term_students(term_id)
