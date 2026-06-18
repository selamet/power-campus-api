"""Schedule orchestration: settings, config, generation, apply, manual edits."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.schedule.models import ScheduleConfig, TermScheduleSettings
from app.apps.schedule.repository import ScheduleRepository
from app.apps.schedule.schemas import (
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    TermSettingsOut,
    TermSettingsUpdate,
)


def _settings_out(s: TermScheduleSettings) -> TermSettingsOut:
    return TermSettingsOut(
        term_id=s.term_id,
        working_days=s.working_days,
        day_start=s.day_start,
        day_end=s.day_end,
        default_duration=s.default_duration,
        default_per_day=s.default_per_day,
        break_min=s.break_min,
        teacher_rules=s.teacher_rules,
    )


class ScheduleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ScheduleRepository(session)

    async def get_settings(self, term_id: int) -> TermSettingsOut:
        existing = await self._repo.get_settings(term_id)
        if existing is None:
            defaults = TermSettingsUpdate()
            return TermSettingsOut(term_id=term_id, **defaults.model_dump())
        return _settings_out(existing)

    async def upsert_settings(
        self, term_id: int, payload: TermSettingsUpdate
    ) -> TermSettingsOut:
        existing = await self._repo.get_settings(term_id)
        data = payload.model_dump()
        if existing is None:
            existing = TermScheduleSettings(term_id=term_id, **data)
            self._repo.add(existing)
        else:
            for key, value in data.items():
                setattr(existing, key, value)
        await self._session.commit()
        await self._session.refresh(existing)
        return _settings_out(existing)

    async def get_config(self, class_id: int) -> ScheduleConfigOut:
        existing = await self._repo.get_config(class_id)
        rules = existing.rules if existing else {}
        return ScheduleConfigOut(class_id=class_id, rules=rules)

    async def upsert_config(
        self, class_id: int, payload: ScheduleConfigUpdate
    ) -> ScheduleConfigOut:
        existing = await self._repo.get_config(class_id)
        if existing is None:
            existing = ScheduleConfig(class_id=class_id, rules=payload.rules)
            self._repo.add(existing)
        else:
            existing.rules = payload.rules
        await self._session.commit()
        await self._session.refresh(existing)
        return ScheduleConfigOut(class_id=existing.class_id, rules=existing.rules)
