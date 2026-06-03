"""Data-access helpers for students and their enrollments."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.students.models import Student

_CODE_PREFIX = "PA-"
_CODE_FLOOR = 1059  # first generated code is PA-1060


class StudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Student]:
        """All students (newest first) with their enrollments eagerly loaded."""
        result = await self._session.scalars(
            select(Student)
            .options(selectinload(Student.enrollments))
            .order_by(Student.id.desc())
        )
        return list(result)

    async def get_by_code(self, code: str) -> Student | None:
        result = await self._session.scalars(
            select(Student)
            .where(Student.student_code == code)
            .options(selectinload(Student.enrollments))
        )
        return result.first()

    async def next_student_code(self) -> str:
        """Generate the next sequential public code, e.g. ``PA-1060``."""
        codes = list(await self._session.scalars(select(Student.student_code)))
        highest = _CODE_FLOOR
        for code in codes:
            suffix = code.removeprefix(_CODE_PREFIX)
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return f"{_CODE_PREFIX}{highest + 1}"

    def add(self, student: Student) -> None:
        self._session.add(student)

    async def delete(self, student: Student) -> None:
        await self._session.delete(student)
