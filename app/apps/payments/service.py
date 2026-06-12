"""Installment scheduling and payment collection use cases."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.payments.models import Installment, Payment
from app.apps.payments.schedule import allocate, build_schedule, next_due_date
from app.apps.payments.schemas import InstallmentOut, PaymentOut, RecordPaymentRequest
from app.apps.students.models import Enrollment, Student
from app.apps.students.repository import StudentRepository
from app.apps.students.schemas import StudentOut
from app.apps.students.service import StudentNotFoundError


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._students = StudentRepository(session)

    def generate_schedule(self, enrollment: Enrollment) -> list[Installment]:
        """Create the installment rows for an enrollment and set its next due date.

        Anything already collected (the opening payment) is deducted up front,
        so the installments split the remaining balance equally instead of the
        full fee.
        """
        financed = max(enrollment.fee - enrollment.paid, 0)
        rows = build_schedule(financed, enrollment.plan, enrollment.start_at) if financed else []
        installments = [
            Installment(
                enrollment_id=enrollment.id,
                sequence=seq,
                amount=amount,
                due_date=due,
                paid_amount=0,
            )
            for seq, amount, due in rows
        ]
        self._session.add_all(installments)
        enrollment.next_payment_at = next_due_date(installments)
        return installments

    async def ensure_schedule(self, enrollment: Enrollment) -> None:
        """Generate the schedule once; a no-op if it already exists."""
        if not await self._installments_for(enrollment.id):
            self.generate_schedule(enrollment)

    async def list_installments(self, code: str) -> list[InstallmentOut]:
        _, enrollment = await self._resolve(code)
        today = date.today()
        return [
            InstallmentOut.from_model(item, today)
            for item in await self._installments_for(enrollment.id)
        ]

    async def list_payments(self, code: str) -> list[PaymentOut]:
        _, enrollment = await self._resolve(code)
        payments = await self._session.scalars(
            select(Payment)
            .where(Payment.enrollment_id == enrollment.id)
            .order_by(Payment.paid_at.desc(), Payment.id.desc())
        )
        return [PaymentOut.model_validate(payment) for payment in payments]

    async def record_payment(self, code: str, payload: RecordPaymentRequest) -> StudentOut:
        """Record a collected payment and re-spread it across the schedule."""
        student, enrollment = await self._resolve(code)
        self._session.add(
            Payment(
                enrollment_id=enrollment.id,
                amount=payload.amount,
                paid_at=payload.paid_at,
                method=payload.method,
                note=payload.note,
            )
        )
        await self._session.flush()

        total = int(
            await self._session.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.enrollment_id == enrollment.id
                )
            )
            or 0
        )
        installments = await self._installments_for(enrollment.id)
        if installments:
            # The schedule covers fee minus the opening payment collected
            # before it existed — only spread what came in afterwards.
            opening = enrollment.fee - sum(item.amount for item in installments)
            allocate(max(total - opening, 0), installments)
            enrollment.next_payment_at = next_due_date(installments)
        enrollment.paid = total
        await self._session.commit()
        return StudentOut.from_models(student)

    async def _installments_for(self, enrollment_id: int) -> list[Installment]:
        result = await self._session.scalars(
            select(Installment)
            .where(Installment.enrollment_id == enrollment_id)
            .order_by(Installment.sequence)
        )
        return list(result)

    async def _resolve(self, code: str) -> tuple[Student, Enrollment]:
        student = await self._students.get_by_code(code)
        if student is None or not student.enrollments:
            raise StudentNotFoundError(code)
        return student, student.enrollments[-1]
