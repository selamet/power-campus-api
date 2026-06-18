"""Class-lesson use cases: CRUD and default seeding on class creation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.classes.lessons import LessonType
from app.apps.classes.models import ClassLesson, SchoolClass
from app.apps.classes.schemas import ClassLessonOut, LessonInput, LessonUpdate
from app.apps.classes.service import (
    ClassNotFoundError,
    InactiveTeacherError,
    TeacherNotFoundError,
)
from app.apps.teachers.models import Teacher, TeacherStatus


class LessonNotFoundError(Exception):
    """Raised when no lesson matches the given id within the class."""


class LessonService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_lessons(self, class_id: int) -> list[ClassLessonOut]:
        await self._get_class(class_id)
        rows = await self._session.scalars(
            select(ClassLesson)
            .where(ClassLesson.class_id == class_id)
            .order_by(ClassLesson.id)
        )
        return [ClassLessonOut.from_model(row) for row in rows]

    async def add_lesson(self, class_id: int, payload: LessonInput) -> ClassLessonOut:
        school_class = await self._get_class(class_id)
        teacher = await self._resolve_teacher(payload.teacher_id)
        lesson = ClassLesson(
            class_id=school_class.id,
            lesson_type=payload.lesson_type.value,
        )
        lesson.teacher = teacher
        self._session.add(lesson)
        await self._session.commit()
        return ClassLessonOut.from_model(lesson)

    async def update_lesson(
        self, class_id: int, lesson_id: int, payload: LessonUpdate
    ) -> ClassLessonOut:
        lesson = await self._get_lesson(class_id, lesson_id)
        data = payload.model_dump(exclude_unset=True)
        if "teacher_id" in data:
            lesson.teacher = await self._resolve_teacher(data["teacher_id"])
        await self._session.commit()
        return ClassLessonOut.from_model(lesson)

    async def delete_lesson(self, class_id: int, lesson_id: int) -> None:
        lesson = await self._get_lesson(class_id, lesson_id)
        await self._session.delete(lesson)
        await self._session.commit()

    async def seed_for_new_class(
        self, school_class: SchoolClass, lessons: list[LessonInput] | None
    ) -> None:
        """Create the class's lessons. ``None`` seeds the four catalog defaults;
        otherwise creates exactly the provided list. Does not commit."""
        if lessons is None:
            for lesson_type in LessonType:
                lesson = ClassLesson(
                    class_id=school_class.id,
                    lesson_type=lesson_type.value,
                )
                self._session.add(lesson)
        else:
            for item in lessons:
                teacher = await self._resolve_teacher(item.teacher_id)
                lesson = ClassLesson(
                    class_id=school_class.id,
                    lesson_type=LessonType(item.lesson_type).value,
                )
                lesson.teacher = teacher
                self._session.add(lesson)

    async def _resolve_teacher(self, teacher_id: int | None) -> Teacher | None:
        if teacher_id is None:
            return None
        teacher = await self._session.get(Teacher, teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        if teacher.status is not TeacherStatus.active:
            raise InactiveTeacherError(teacher_id)
        return teacher

    async def _get_class(self, class_id: int) -> SchoolClass:
        school_class = await self._session.get(SchoolClass, class_id)
        if school_class is None:
            raise ClassNotFoundError(class_id)
        return school_class

    async def _get_lesson(self, class_id: int, lesson_id: int) -> ClassLesson:
        await self._get_class(class_id)
        lesson = await self._session.get(ClassLesson, lesson_id)
        if lesson is None or lesson.class_id != class_id:
            raise LessonNotFoundError(lesson_id)
        return lesson
