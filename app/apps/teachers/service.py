"""Teacher management use cases."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.classes.schemas import ClassOut
from app.apps.students.models import Enrollment
from app.apps.teachers.models import Teacher, TeacherStatus
from app.apps.teachers.repository import TeacherRepository
from app.apps.teachers.schemas import TeacherCreate, TeacherOut, TeacherUpdate

_EDITABLE = frozenset({"name", "email", "phone", "status", "languages", "levels", "note"})


class TeacherNotFoundError(Exception):
    """Raised when no teacher matches the given id."""


class TeacherService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TeacherRepository(session)

    async def list_teachers(self, *, status: TeacherStatus | None = None) -> list[TeacherOut]:
        teachers = await self._repo.list_all(status=status)
        counts = await self._repo.class_counts()
        return [
            TeacherOut.from_model(t, class_count=counts.get(t.id, 0)) for t in teachers
        ]

    async def get_teacher(self, teacher_id: int) -> TeacherOut:
        teacher = await self._get_or_404(teacher_id)
        count = await self._repo.class_count_for(teacher_id)
        return TeacherOut.from_model(teacher, class_count=count)

    async def create_teacher(self, payload: TeacherCreate) -> TeacherOut:
        teacher = Teacher(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            status=payload.status,
            languages=payload.languages,
            levels=payload.levels,
            note=payload.note,
        )
        self._repo.add(teacher)
        await self._session.commit()
        return TeacherOut.from_model(teacher, class_count=0)

    async def update_teacher(self, teacher_id: int, payload: TeacherUpdate) -> TeacherOut:
        teacher = await self._get_or_404(teacher_id)
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            if field in _EDITABLE:
                setattr(teacher, field, value)
        await self._session.commit()
        count = await self._repo.class_count_for(teacher_id)
        return TeacherOut.from_model(teacher, class_count=count)

    async def list_classes(self, teacher_id: int) -> list[ClassOut]:
        await self._get_or_404(teacher_id)
        classes = await self._repo.classes_for(teacher_id)
        today = date.today()
        counts = dict(
            (
                await self._session.execute(
                    select(Enrollment.class_id, func.count())
                    .where(Enrollment.class_id.is_not(None))
                    .group_by(Enrollment.class_id)
                )
            ).all()
        )
        return [
            ClassOut.from_model(c, student_count=counts.get(c.id, 0), today=today)
            for c in classes
        ]

    async def _get_or_404(self, teacher_id: int) -> Teacher:
        teacher = await self._repo.get_by_id(teacher_id)
        if teacher is None:
            raise TeacherNotFoundError(teacher_id)
        return teacher
