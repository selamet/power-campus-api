"""Class (section) management use cases."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.classes.models import SchoolClass
from app.apps.classes.naming import level_code
from app.apps.classes.repository import ClassRepository
from app.apps.classes.schemas import (
    AssignStudentsRequest,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    CreateClassRequest,
)
from app.apps.students.models import Enrollment, EnrollmentStatus, Student
from app.apps.terms.models import Term


class ClassNotFoundError(Exception):
    """Raised when no class matches the given id."""


class TermNotFoundError(Exception):
    """Raised when creating a class against a term that does not exist."""


class DuplicateClassError(Exception):
    """Raised when a term already has a class with the same level and section."""


class ClassService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ClassRepository(session)

    async def list_classes(self, *, term_id: int | None = None) -> list[ClassOut]:
        today = date.today()
        classes = await self._repo.list_all(term_id=term_id)
        counts = await self._student_counts()
        return [
            ClassOut.from_model(item, student_count=counts.get(item.id, 0), today=today)
            for item in classes
        ]

    async def create_class(self, payload: CreateClassRequest) -> ClassOut:
        term = await self._session.get(Term, payload.term_id)
        if term is None:
            raise TermNotFoundError(payload.term_id)
        section = payload.section
        if section is None:
            section = await self._repo.next_section(payload.term_id, payload.level)
        school_class = SchoolClass(
            term_id=payload.term_id, level=payload.level, section=section
        )
        self._repo.add(school_class)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateClassError(payload.term_id) from exc
        return await self._to_out(school_class)

    async def update_class(self, class_id: int, payload: ClassUpdate) -> ClassOut:
        school_class = await self._get_or_404(class_id)
        data = payload.model_dump(exclude_unset=True)
        if data.get("level") is not None:
            school_class.level = data["level"]
        if data.get("section") is not None:
            school_class.section = data["section"]
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateClassError(class_id) from exc
        return await self._to_out(school_class)

    async def delete_class(self, class_id: int) -> None:
        school_class = await self._get_or_404(class_id)
        await self._repo.delete(school_class)
        await self._session.commit()

    async def list_class_students(self, class_id: int) -> list[ClassStudentOut]:
        """The students assigned to a class, by name."""
        rows = await self._session.execute(
            select(Enrollment, Student)
            .join(Student, Enrollment.student_id == Student.id)
            .where(Enrollment.class_id == class_id)
            .order_by(Student.name)
        )
        return [
            ClassStudentOut(
                student_id=student.student_code,
                name=student.name,
                level=enrollment.level,
                status=enrollment.status,
            )
            for enrollment, student in rows
        ]

    async def assign_students(
        self, class_id: int, payload: AssignStudentsRequest
    ) -> list[ClassStudentOut]:
        """Assign existing term students to a class.

        Only active students already enrolled in the class's term are assigned;
        a student in another class of the same term is moved here. Students not
        in the term, or not active, are skipped.
        """
        school_class = await self._get_or_404(class_id)
        students = list(
            await self._session.scalars(
                select(Student)
                .where(Student.student_code.in_(payload.student_codes))
                .options(selectinload(Student.enrollments))
            )
        )
        for student in students:
            enrollment = self._term_enrollment(student, school_class.term_id)
            if enrollment is None or enrollment.status is not EnrollmentStatus.active:
                continue
            enrollment.class_id = class_id
        await self._session.commit()
        return await self.list_class_students(class_id)

    async def auto_assign(self, class_id: int) -> list[ClassStudentOut]:
        """Assign every active, still-unassigned student in the term whose level
        matches the class level."""
        school_class = await self._get_or_404(class_id)
        target = level_code(school_class.level)
        enrollments = list(
            await self._session.scalars(
                select(Enrollment).where(
                    Enrollment.term_id == school_class.term_id,
                    Enrollment.class_id.is_(None),
                    Enrollment.status == EnrollmentStatus.active,
                )
            )
        )
        for enrollment in enrollments:
            if level_code(enrollment.level) == target:
                enrollment.class_id = class_id
        await self._session.commit()
        return await self.list_class_students(class_id)

    async def unassign_student(self, class_id: int, code: str) -> None:
        await self._get_or_404(class_id)
        enrollment = await self._session.scalar(
            select(Enrollment)
            .join(Student, Enrollment.student_id == Student.id)
            .where(Enrollment.class_id == class_id, Student.student_code == code)
        )
        if enrollment is not None:
            enrollment.class_id = None
            await self._session.commit()

    async def _student_counts(self) -> dict[int, int]:
        rows = await self._session.execute(
            select(Enrollment.class_id, func.count())
            .where(Enrollment.class_id.is_not(None))
            .group_by(Enrollment.class_id)
        )
        return dict(rows.all())

    def _term_enrollment(self, student: Student, term_id: int) -> Enrollment | None:
        for enrollment in student.enrollments:
            if enrollment.term_id == term_id:
                return enrollment
        return None

    async def _to_out(self, school_class: SchoolClass) -> ClassOut:
        count = await self._session.scalar(
            select(func.count()).where(Enrollment.class_id == school_class.id)
        )
        return ClassOut.from_model(
            school_class, student_count=int(count or 0), today=date.today()
        )

    async def _get_or_404(self, class_id: int) -> SchoolClass:
        school_class = await self._repo.get_by_id(class_id)
        if school_class is None:
            raise ClassNotFoundError(class_id)
        return school_class
