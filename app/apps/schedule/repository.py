"""Schedule data access."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.schedule.models import ScheduleConfig, TermScheduleSettings

if TYPE_CHECKING:
    from app.apps.classes.models import ClassLesson
    from app.apps.schedule.models import ScheduleRuleTemplate, ScheduleSession


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

    async def sessions_for_classes(self, class_ids: list[int]) -> list["ScheduleSession"]:
        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.models import ScheduleSession

        return list(
            await self._session.scalars(
                select(ScheduleSession)
                .join(ClassLesson, ScheduleSession.class_lesson_id == ClassLesson.id)
                .where(ClassLesson.class_id.in_(class_ids))
            )
        )

    async def sessions_for_teacher(self, teacher_id: int) -> list["ScheduleSession"]:
        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.models import ScheduleSession

        return list(
            await self._session.scalars(
                select(ScheduleSession)
                .join(ClassLesson, ScheduleSession.class_lesson_id == ClassLesson.id)
                .where(ClassLesson.teacher_id == teacher_id)
            )
        )

    async def sessions_for_term(self, term_id: int, weekday: int | None) -> list["ScheduleSession"]:
        from app.apps.classes.models import ClassLesson, SchoolClass
        from app.apps.schedule.models import ScheduleSession

        stmt = (
            select(ScheduleSession)
            .join(ClassLesson, ScheduleSession.class_lesson_id == ClassLesson.id)
            .join(SchoolClass, ClassLesson.class_id == SchoolClass.id)
            .where(SchoolClass.term_id == term_id)
        )
        if weekday is not None:
            stmt = stmt.where(ScheduleSession.weekday == weekday)
        return list(await self._session.scalars(stmt))

    async def class_lessons_for_class(self, class_id: int) -> list["ClassLesson"]:
        from app.apps.classes.models import ClassLesson

        return list(
            await self._session.scalars(
                select(ClassLesson).where(ClassLesson.class_id == class_id)
            )
        )

    async def class_lessons_for_term(self, term_id: int) -> list["ClassLesson"]:
        from app.apps.classes.models import ClassLesson, SchoolClass

        return list(
            await self._session.scalars(
                select(ClassLesson)
                .join(SchoolClass, ClassLesson.class_id == SchoolClass.id)
                .where(SchoolClass.term_id == term_id)
            )
        )

    async def configs_for_classes(self, class_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not class_ids:
            return {}
        rows = await self._session.scalars(
            select(ScheduleConfig).where(ScheduleConfig.class_id.in_(class_ids))
        )
        return {c.class_id: c.rules for c in rows}

    async def delete_sessions_for_classes(self, class_ids: list[int]) -> None:
        from sqlalchemy import delete

        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.models import ScheduleSession

        if not class_ids:
            return
        cl_ids = list(
            await self._session.scalars(
                select(ClassLesson.id).where(ClassLesson.class_id.in_(class_ids))
            )
        )
        if not cl_ids:
            return
        await self._session.execute(
            delete(ScheduleSession).where(ScheduleSession.class_lesson_id.in_(cl_ids))
        )

    async def locked_sessions_for_classes(self, class_ids: list[int]) -> list["ScheduleSession"]:
        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.models import ScheduleSession

        if not class_ids:
            return []
        return list(
            await self._session.scalars(
                select(ScheduleSession)
                .join(ClassLesson, ScheduleSession.class_lesson_id == ClassLesson.id)
                .where(ClassLesson.class_id.in_(class_ids))
                .where(ScheduleSession.locked.is_(True))
            )
        )

    async def delete_unlocked_sessions_for_classes(self, class_ids: list[int]) -> None:
        from sqlalchemy import delete

        from app.apps.classes.models import ClassLesson
        from app.apps.schedule.models import ScheduleSession

        if not class_ids:
            return
        cl_ids = list(
            await self._session.scalars(
                select(ClassLesson.id).where(ClassLesson.class_id.in_(class_ids))
            )
        )
        if not cl_ids:
            return
        await self._session.execute(
            delete(ScheduleSession)
            .where(ScheduleSession.class_lesson_id.in_(cl_ids))
            .where(ScheduleSession.locked.is_(False))
        )

    async def get_session_by_id(self, session_id: int) -> "ScheduleSession | None":
        from app.apps.schedule.models import ScheduleSession

        return await self._session.get(ScheduleSession, session_id)

    async def sessions_for_term_of_class_lesson(
        self, class_lesson_id: int
    ) -> list["ScheduleSession"]:
        """All sessions in the same term as the given class_lesson (for conflict scan)."""
        from app.apps.classes.models import ClassLesson, SchoolClass

        cl = await self._session.get(ClassLesson, class_lesson_id)
        if cl is None:
            return []
        sub_class = await self._session.get(SchoolClass, cl.class_id)
        if sub_class is None:
            return []
        return await self.sessions_for_term(sub_class.term_id, None)

    async def delete_session(self, obj: "ScheduleSession") -> None:
        await self._session.delete(obj)

    async def list_rule_templates(self) -> list["ScheduleRuleTemplate"]:
        from app.apps.schedule.models import ScheduleRuleTemplate

        return list(
            await self._session.scalars(
                select(ScheduleRuleTemplate).order_by(ScheduleRuleTemplate.name)
            )
        )

    async def get_rule_template_by_name(self, name: str) -> "ScheduleRuleTemplate | None":
        from app.apps.schedule.models import ScheduleRuleTemplate

        return await self._session.scalar(  # type: ignore[no-any-return]
            select(ScheduleRuleTemplate).where(ScheduleRuleTemplate.name == name)
        )

    async def get_rule_template(self, template_id: int) -> "ScheduleRuleTemplate | None":
        from app.apps.schedule.models import ScheduleRuleTemplate

        return await self._session.get(ScheduleRuleTemplate, template_id)

    async def delete_rule_template(self, obj: "ScheduleRuleTemplate") -> None:
        await self._session.delete(obj)
