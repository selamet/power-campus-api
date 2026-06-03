"""Installment and payment schemas."""

from datetime import date

from pydantic import Field

from app.apps.payments.models import Installment
from app.core.schemas import CamelModel


class InstallmentOut(CamelModel):
    sequence: int
    amount: int
    due_date: date
    paid_amount: int
    status: str  # "paid" | "partial" | "overdue" | "pending"

    @classmethod
    def from_model(cls, installment: Installment, today: date) -> "InstallmentOut":
        if installment.paid_amount >= installment.amount:
            status = "paid"
        elif installment.paid_amount > 0:
            status = "partial"
        elif installment.due_date < today:
            status = "overdue"
        else:
            status = "pending"
        return cls(
            sequence=installment.sequence,
            amount=installment.amount,
            due_date=installment.due_date,
            paid_amount=installment.paid_amount,
            status=status,
        )


class PaymentOut(CamelModel):
    id: int
    amount: int
    paid_at: date
    method: str
    note: str | None


class RecordPaymentRequest(CamelModel):
    amount: int = Field(gt=0)
    paid_at: date
    method: str
    note: str | None = None
