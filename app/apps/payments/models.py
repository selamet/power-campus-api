"""Installment schedule and payment (collection) models."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import AuditedBase


class Installment(AuditedBase):
    """A single scheduled payment within an enrollment's plan."""

    __tablename__ = "installments"

    enrollment_id: Mapped[int] = mapped_column(
        "enrollmentId",
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column("dueDate", Date, nullable=False)
    # How much of this installment has been covered by collected payments.
    paid_amount: Mapped[int] = mapped_column(
        "paidAmount", Integer, server_default="0", nullable=False
    )


class Payment(AuditedBase):
    """A collected payment, recorded by staff and applied to the schedule."""

    __tablename__ = "payments"

    enrollment_id: Mapped[int] = mapped_column(
        "enrollmentId",
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_at: Mapped[date] = mapped_column("paidAt", Date, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
