"""Data-access helpers for students and their enrollments."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.students.models import Student, StudentActivity

_CODE_PREFIX = "PA-"
_CODE_OFFSET = 1059  # the first student (id=1) gets PA-1060


def provisional_code() -> str:
    """A unique placeholder satisfying the NOT NULL/unique code column until the
    real, id-derived code is assigned after the row is flushed."""
    return f"tmp-{uuid4().hex}"


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[Student]:
        """Students (newest first) with their enrollments eagerly loaded."""
        stmt = (
            select(Student)
            .options(selectinload(Student.enrollments))
            .order_by(Student.id.desc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_by_code(self, code: str) -> Student | None:
        result = await self._session.scalars(
            select(Student)
            .where(Student.student_code == code)
            .options(selectinload(Student.enrollments))
        )
        return result.first()

    async def get_by_tckn(self, tckn: str) -> Student | None:
        result = await self._session.scalars(
            select(Student)
            .where(Student.tckn == tckn)
            .options(selectinload(Student.enrollments))
        )
        return result.first()

    async def get_by_passport(self, passport_no: str) -> Student | None:
        result = await self._session.scalars(
            select(Student)
            .where(Student.passport_no == passport_no)
            .options(selectinload(Student.enrollments))
        )
        return result.first()

    async def get_by_identifier(self, identifier: str) -> Student | None:
        """Resolve a student by any public identifier: TCKN, passport number, or
        the ``PA-…`` code. Used so every endpoint accepts the same handle."""
        for getter in (self.get_by_tckn, self.get_by_passport, self.get_by_code):
            student = await getter(identifier)
            if student is not None:
                return student
        return None

    async def list_activities(self, student_id: int) -> list[StudentActivity]:
        """A student's activity entries, newest first, with the actor loaded."""
        result = await self._session.scalars(
            select(StudentActivity)
            .where(StudentActivity.student_id == student_id)
            .order_by(StudentActivity.created_at.desc(), StudentActivity.id.desc())
            .options(selectinload(StudentActivity.actor))
        )
        return list(result)

    async def assign_public_code(self, student: Student) -> None:
        """Flush to obtain the autoincrement id, then derive a race-free public
        code from it (e.g. ``PA-1060``). Relying on the primary key avoids the
        read-max-then-insert race of a counted sequence."""
        await self._session.flush()
        student.student_code = f"{_CODE_PREFIX}{_CODE_OFFSET + student.id}"

    def add(self, student: Student) -> None:
        self._session.add(student)

    async def delete(self, student: Student) -> None:
        await self._session.delete(student)
