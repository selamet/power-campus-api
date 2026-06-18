"""Schedule data access."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.schedule.models import ScheduleConfig, TermScheduleSettings


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_settings(self, term_id: int) -> TermScheduleSettings | None:
        return await self._session.scalar(  # type: ignore[no-any-return]
            select(TermScheduleSettings).where(TermScheduleSettings.term_id == term_id)
        )

    def add(self, obj: object) -> None:
        self._session.add(obj)

    async def get_config(self, class_id: int) -> ScheduleConfig | None:
        return await self._session.scalar(  # type: ignore[no-any-return]
            select(ScheduleConfig).where(ScheduleConfig.class_id == class_id)
        )
