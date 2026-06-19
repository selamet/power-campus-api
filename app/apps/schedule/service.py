"""Schedule orchestration: settings, config, generation, apply, manual edits."""

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.apps.schedule.generator import LessonReq

from app.apps.schedule.models import ScheduleConfig, ScheduleSession, TermScheduleSettings
from app.apps.schedule.repository import ScheduleRepository
from app.apps.schedule.schemas import (
    ApplyResult,
    GeneratePreview,
    ReportItem,
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    SessionCreate,
    SessionMove,
    SessionOut,
    SessionPreview,
    TermSettingsOut,
    TermSettingsUpdate,
)


class ConflictError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _lt(reqs: list["LessonReq"], class_lesson_id: int) -> str:
    for r in reqs:
        if r.class_lesson_id == class_lesson_id:
            return r.lesson_type
    return ""


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
        day_windows=s.day_windows,
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
        # day_windows values are time objects — serialize to strings for JSON storage
        data["day_windows"] = {
            day: {k: v.isoformat() for k, v in window.items()}
            for day, window in data["day_windows"].items()
        }
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
            locked=s.locked,
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

    async def _build_and_run(self, term_id: int, class_ids: list[int]) -> GeneratePreview:
        from app.apps.classes.lessons import LessonType
        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.generator import (
            ClassRules,
            GenSettings,
            LessonReq,
            TeacherRule,
            generate,
        )

        settings_out = await self.get_settings(term_id)
        day_windows: dict[int, tuple[time, time]] = {}
        for key, win in settings_out.day_windows.items():
            day_windows[int(key)] = (win["start"], win["end"])
        gs = GenSettings(
            working_days=settings_out.working_days,
            day_start=settings_out.day_start,
            day_end=settings_out.day_end,
            per_day_default=settings_out.default_per_day,
            break_min=settings_out.break_min,
            day_windows=day_windows,
        )
        trules: dict[int, TeacherRule] = {}
        for key, val in settings_out.teacher_rules.items():
            trules[int(key)] = TeacherRule(
                unavailable_weekdays=val.get("unavailableWeekdays", []),
                max_per_day=val.get("maxPerDay"),
                max_per_week=val.get("maxPerWeek"),
            )
        configs = await self._repo.configs_for_classes(class_ids)
        lessons_by_class: dict[int, list[ClassLesson]] = {}
        for cl in await self._repo.class_lessons_for_term(term_id):
            lessons_by_class.setdefault(cl.class_id, []).append(cl)

        reqs: list[LessonReq] = []
        crules: dict[int, ClassRules] = {}
        teacher_names: dict[int | None, str | None] = {None: None}
        for cid in class_ids:
            rules = configs.get(cid, {})
            crules[cid] = ClassRules(
                per_day_cap=rules.get("perDayCap"),
                closed_weekdays=rules.get("closedWeekdays", []),
                daily_pattern=rules.get("dailyPattern", []),
                separations=rules.get("separations", []),
            )
            cfg_lessons = {item["lessonType"]: item for item in rules.get("lessons", [])}
            for cl in lessons_by_class.get(cid, []):
                teacher_names[cl.teacher_id] = cl.teacher.name if cl.teacher else None
                # A lesson without an explicit builder rule still gets scheduled
                # with sensible defaults (default duration, one session/week), so
                # generation works out of the box; the builder overrides per lesson.
                spec = cfg_lessons.get(cl.lesson_type, {})
                reqs.append(
                    LessonReq(
                        class_lesson_id=cl.id,
                        class_id=cid,
                        teacher_id=cl.teacher_id,
                        lesson_type=cl.lesson_type,
                        duration_min=spec.get("durationMin", settings_out.default_duration),
                        count=spec.get("sessionsPerWeek", 1),
                        pinned_weekday=spec.get("pinnedWeekday"),
                        consecutive=spec.get("consecutive", False),
                    )
                )

        result = generate(reqs, gs, crules, trules)
        sessions = [
            SessionPreview(
                class_lesson_id=p.class_lesson_id,
                class_id=p.class_id,
                lesson_type=LessonType(_lt(reqs, p.class_lesson_id)),
                teacher_id=p.teacher_id,
                teacher_name=teacher_names.get(p.teacher_id),
                weekday=p.weekday,
                start_time=p.start,
                end_time=p.end,
            )
            for p in result.placements
        ]
        report = [
            ReportItem(
                class_id=u.class_id,
                lesson_type=LessonType(u.lesson_type),
                reason=u.reason,
            )
            for u in result.unplaced
        ]
        return GeneratePreview(sessions=sessions, report=report)

    async def generate_for_class(self, class_id: int) -> GeneratePreview:
        from app.apps.classes.models import SchoolClass

        cls = await self._session.get(SchoolClass, class_id)
        if cls is None:
            return GeneratePreview(sessions=[], report=[])
        return await self._build_and_run(cls.term_id, [class_id])

    async def generate_for_term(self, term_id: int) -> GeneratePreview:
        from app.apps.classes.models import SchoolClass

        ids = list(
            await self._session.scalars(
                select(SchoolClass.id).where(SchoolClass.term_id == term_id)
            )
        )
        return await self._build_and_run(term_id, ids)

    async def _apply(self, term_id: int, class_ids: list[int]) -> ApplyResult:
        preview = await self._build_and_run(term_id, class_ids)
        await self._repo.delete_sessions_for_classes(class_ids)
        for s in preview.sessions:
            self._repo.add(
                ScheduleSession(
                    class_lesson_id=s.class_lesson_id,
                    weekday=s.weekday,
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
            )
        await self._session.commit()
        return ApplyResult(applied=len(preview.sessions), report=preview.report)

    async def apply_for_class(self, class_id: int) -> ApplyResult:
        from app.apps.classes.models import SchoolClass

        cls = await self._session.get(SchoolClass, class_id)
        if cls is None:
            return ApplyResult(applied=0, report=[])
        return await self._apply(cls.term_id, [class_id])

    async def apply_for_term(self, term_id: int) -> ApplyResult:
        from app.apps.classes.models import SchoolClass

        ids = list(
            await self._session.scalars(
                select(SchoolClass.id).where(SchoolClass.term_id == term_id)
            )
        )
        return await self._apply(term_id, ids)

    async def _assert_no_conflict(
        self,
        class_lesson_id: int,
        weekday: int,
        start: time,
        end: time,
        *,
        exclude_id: int | None = None,
    ) -> None:
        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.conflicts import Slot, overlaps

        cl = await self._session.get(ClassLesson, class_lesson_id)
        if cl is None:
            raise ConflictError("Ders bulunamadı.")
        new = Slot(weekday, start, end)
        for s in await self._repo.sessions_for_term_of_class_lesson(class_lesson_id):
            if exclude_id is not None and s.id == exclude_id:
                continue
            if not overlaps(new, Slot(s.weekday, s.start_time, s.end_time)):
                continue
            other = s.class_lesson
            if other.class_id == cl.class_id:
                raise ConflictError("Bu sınıfın aynı saatte başka dersi var.")
            if cl.teacher_id is not None and other.teacher_id == cl.teacher_id:
                raise ConflictError("Öğretmen aynı saatte başka sınıfta.")

    async def add_session(self, payload: SessionCreate) -> SessionOut:
        await self._assert_no_conflict(
            payload.class_lesson_id, payload.weekday, payload.start_time, payload.end_time
        )
        obj = ScheduleSession(
            class_lesson_id=payload.class_lesson_id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        self._repo.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return self._session_out(obj)

    async def move_session(self, session_id: int, payload: SessionMove) -> SessionOut:
        obj = await self._repo.get_session_by_id(session_id)
        if obj is None:
            raise ConflictError("Oturum bulunamadı.")
        if obj.locked:
            raise ConflictError("Kilitli oturum taşınamaz. Önce kilidi açın.")
        await self._assert_no_conflict(
            obj.class_lesson_id,
            payload.weekday,
            payload.start_time,
            payload.end_time,
            exclude_id=session_id,
        )
        obj.weekday = payload.weekday
        obj.start_time = payload.start_time
        obj.end_time = payload.end_time
        await self._session.commit()
        await self._session.refresh(obj)
        return self._session_out(obj)

    async def delete_session(self, session_id: int) -> bool:
        obj = await self._repo.get_session_by_id(session_id)
        if obj is None:
            return False
        if obj.locked:
            raise ConflictError("Kilitli oturum silinemez. Önce kilidi açın.")
        await self._repo.delete_session(obj)
        await self._session.commit()
        return True

    async def set_lock(self, session_id: int, locked: bool) -> SessionOut:
        obj = await self._repo.get_session_by_id(session_id)
        if obj is None:
            raise ConflictError("Oturum bulunamadı.")
        obj.locked = locked
        await self._session.commit()
        await self._session.refresh(obj)
        return self._session_out(obj)
