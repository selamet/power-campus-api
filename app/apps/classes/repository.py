"""Data-access helpers for classes."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.classes.models import SchoolClass


class ClassRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, term_id: int | None = None) -> list[SchoolClass]:
        """Classes, newest term first then by level/section."""
        stmt = select(SchoolClass).order_by(
            SchoolClass.term_id.desc(), SchoolClass.level, SchoolClass.section
        )
        if term_id is not None:
            stmt = stmt.where(SchoolClass.term_id == term_id)
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_by_id(self, class_id: int) -> SchoolClass | None:
        return await self._session.get(SchoolClass, class_id)

    async def next_section(self, term_id: int, level: str) -> int:
        """The next free section number for a term+level (1 when none yet)."""
        current = await self._session.scalar(
            select(func.max(SchoolClass.section)).where(
                SchoolClass.term_id == term_id, SchoolClass.level == level
            )
        )
        return (current or 0) + 1

    def add(self, school_class: SchoolClass) -> None:
        self._session.add(school_class)

    async def delete(self, school_class: SchoolClass) -> None:
        await self._session.delete(school_class)
