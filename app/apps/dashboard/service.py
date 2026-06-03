"""Dashboard aggregation use cases (read-only)."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.dashboard.schemas import ActivityItem, DashboardStats
from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource

_ACTIVITY_LIMIT = 6


def _relative_time(value: datetime) -> str:
    """Turkish relative time label for an audit timestamp."""
    moment = value if value.tzinfo else value.replace(tzinfo=UTC)
    seconds = (datetime.now(UTC) - moment).total_seconds()
    if seconds < 60:
        return "az önce"
    if seconds < 3600:
        return f"{int(seconds // 60)} dk önce"
    if seconds < 86_400:
        return f"{int(seconds // 3600)} saat önce"
    if seconds < 172_800:
        return "Dün"
    return f"{int(seconds // 86_400)} gün önce"


def _describe(student: Student, status: EnrollmentStatus | None) -> tuple[str, str, str]:
    """Return (what, icon, kind) describing the student's latest activity."""
    if student.source is StudentSource.invite:
        if status is EnrollmentStatus.pending:
            return "hoşgeldin formunu doldurdu, onay bekliyor", "clipboard", "accent"
        return "davet ile kaydını tamamladı", "checkCircle", "ok"
    if student.source is StudentSource.manual:
        return "manuel olarak kaydedildi", "plus", "neutral"
    if status is EnrollmentStatus.pending:
        return "kaydı onay bekliyor", "clipboard", "accent"
    if status is EnrollmentStatus.active:
        return "kaydı oluşturuldu", "plus", "neutral"
    return "kaydı güncellendi", "info", "neutral"


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def stats(self) -> DashboardStats:
        total_students = await self._session.scalar(select(func.count()).select_from(Student)) or 0
        active = await self._count_by_status(EnrollmentStatus.active)
        pending = await self._count_by_status(EnrollmentStatus.pending)
        collected = await self._session.scalar(select(func.coalesce(func.sum(Enrollment.paid), 0)))
        billed = await self._session.scalar(select(func.coalesce(func.sum(Enrollment.fee), 0)))
        return DashboardStats(
            total_students=total_students,
            active_students=active,
            pending_approvals=pending,
            total_collected=int(collected or 0),
            outstanding=int((billed or 0) - (collected or 0)),
        )

    async def activity(self) -> list[ActivityItem]:
        students = list(
            await self._session.scalars(
                select(Student)
                .options(selectinload(Student.enrollments))
                .order_by(Student.created_at.desc())
                .limit(_ACTIVITY_LIMIT)
            )
        )
        items: list[ActivityItem] = []
        for student in students:
            status = student.enrollments[-1].status if student.enrollments else None
            what, icon, kind = _describe(student, status)
            items.append(
                ActivityItem(
                    who=student.name,
                    what=what,
                    icon=icon,
                    kind=kind,
                    time=_relative_time(student.created_at),
                )
            )
        return items

    async def _count_by_status(self, status: EnrollmentStatus) -> int:
        result = await self._session.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.status == status)
        )
        return result or 0
