"""Dashboard aggregation use cases (read-only)."""

from collections import Counter
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.apps.dashboard.schemas import ActivityItem, DashboardStats, MonthlyPoint, OverdueItem
from app.apps.invites.models import Invite, InviteStatus
from app.apps.payments.models import Installment, Payment
from app.apps.students.models import Enrollment, EnrollmentStatus, Student, StudentSource

_ACTIVITY_LIMIT = 6
_OVERDUE_LIMIT = 6
_MONTHLY_WINDOW = 6

_TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

# An installment that still owes money.
_UNPAID = Installment.paid_amount < Installment.amount


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

        today = date.today()
        due_today = (
            await self._session.scalar(
                select(func.count())
                .select_from(Installment)
                .where(Installment.due_date == today, _UNPAID)
            )
            or 0
        )
        overdue_count, overdue_total = (
            await self._session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(Installment.amount - Installment.paid_amount), 0),
                ).where(Installment.due_date < today, _UNPAID)
            )
        ).one()
        invites_pending = await self._count_invites(InviteStatus.pending)
        invites_completed = await self._count_invites(InviteStatus.completed)

        return DashboardStats(
            total_students=total_students,
            active_students=active,
            pending_approvals=pending,
            total_collected=int(collected or 0),
            outstanding=int((billed or 0) - (collected or 0)),
            due_today=due_today,
            overdue_count=int(overdue_count or 0),
            overdue_total=int(overdue_total or 0),
            invites_pending=invites_pending,
            invites_completed=invites_completed,
        )

    async def overdue(self) -> list[OverdueItem]:
        """Oldest unpaid installments whose due date has passed."""
        rows = await self._session.execute(
            select(Installment, Student)
            .join(Enrollment, Installment.enrollment_id == Enrollment.id)
            .join(Student, Enrollment.student_id == Student.id)
            .where(Installment.due_date < date.today(), _UNPAID)
            .order_by(Installment.due_date)
            .limit(_OVERDUE_LIMIT)
        )
        return [
            OverdueItem(
                student_id=student.student_code,
                name=student.name,
                sequence=installment.sequence,
                due_date=installment.due_date,
                amount=installment.amount - (installment.paid_amount or 0),
            )
            for installment, student in rows
        ]

    async def monthly(self) -> list[MonthlyPoint]:
        """Expected vs collected totals for the last six calendar months."""
        today = date.today()
        months: list[tuple[int, int]] = []
        for offset in range(_MONTHLY_WINDOW - 1, -1, -1):
            index = today.month - 1 - offset
            months.append((today.year + index // 12, index % 12 + 1))

        expected: Counter[tuple[int, int]] = Counter()
        for installment in await self._session.scalars(select(Installment)):
            key = (installment.due_date.year, installment.due_date.month)
            expected[key] += installment.amount

        collected: Counter[tuple[int, int]] = Counter()
        for payment in await self._session.scalars(select(Payment)):
            key = (payment.paid_at.year, payment.paid_at.month)
            collected[key] += payment.amount

        return [
            MonthlyPoint(
                month=f"{year:04d}-{month:02d}",
                label=_TR_MONTHS[month - 1],
                expected=expected[(year, month)],
                collected=collected[(year, month)],
            )
            for year, month in months
        ]

    async def _count_invites(self, status: InviteStatus) -> int:
        result = await self._session.scalar(
            select(func.count()).select_from(Invite).where(Invite.status == status)
        )
        return result or 0

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
