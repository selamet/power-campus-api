"""Data-access helpers for teachers."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.classes.models import SchoolClass
from app.apps.teachers.models import Teacher, TeacherStatus


class TeacherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, status: TeacherStatus | None = None) -> list[Teacher]:
        stmt = select(Teacher).order_by(Teacher.name)
        if status is not None:
            stmt = stmt.where(Teacher.status == status)
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_by_id(self, teacher_id: int) -> Teacher | None:
        return await self._session.get(Teacher, teacher_id)

    def add(self, teacher: Teacher) -> None:
        self._session.add(teacher)

    async def class_counts(self) -> dict[int, int]:
        """Assigned-class count per teacher id."""
        rows = await self._session.execute(
            select(SchoolClass.teacher_id, func.count())
            .where(SchoolClass.teacher_id.is_not(None))
            .group_by(SchoolClass.teacher_id)
        )
        return dict(rows.all())

    async def class_count_for(self, teacher_id: int) -> int:
        count = await self._session.scalar(
            select(func.count()).where(SchoolClass.teacher_id == teacher_id)
        )
        return int(count or 0)
