"""Schedule orchestration: settings, config, generation, apply, manual edits."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.apps.schedule.models import ScheduleSession

from app.apps.schedule.models import ScheduleConfig, TermScheduleSettings
from app.apps.schedule.repository import ScheduleRepository
from app.apps.schedule.schemas import (
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    SessionOut,
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

    @staticmethod
    def _session_out(s: "ScheduleSession") -> SessionOut:
        from app.apps.classes.naming import class_display_name

        cl = s.class_lesson
        cls = cl.school_class
        return SessionOut(
            id=s.id,
            class_lesson_id=cl.id,
            class_id=cl.class_id,
            class_name=class_display_name(cls.level, cls.section) if cls else "",
            lesson_type=cl.lesson_type,
            teacher_id=cl.teacher_id,
            teacher_name=cl.teacher.name if cl.teacher else None,
            weekday=s.weekday,
            start_time=s.start_time,
            end_time=s.end_time,
        )

    async def class_schedule(self, class_id: int) -> list[SessionOut]:
        rows = await self._repo.sessions_for_classes([class_id])
        return [self._session_out(s) for s in rows]

    async def teacher_schedule(self, teacher_id: int) -> list[SessionOut]:
        rows = await self._repo.sessions_for_teacher(teacher_id)
        return [self._session_out(s) for s in rows]

    async def term_schedule(self, term_id: int, weekday: int | None) -> list[SessionOut]:
        rows = await self._repo.sessions_for_term(term_id, weekday)
        return [self._session_out(s) for s in rows]
