"""Pure helpers for building installment schedules and allocating payments."""

import calendar
from collections.abc import Iterable
from datetime import date

from app.apps.payments.models import Installment


def installment_count(plan: str) -> int:
    """Number of installments implied by a plan label.

    "Peşin" -> 1, "3 Taksit" -> 3; falls back to 1 when no number is present.
    """
    digits = "".join(ch for ch in plan if ch.isdigit())
    return int(digits) if digits else 1


def add_months(start: date, months: int) -> date:
    """Add whole months to a date, clamping the day to the target month."""
    index = start.month - 1 + months
    year = start.year + index // 12
    month = index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_schedule(fee: int, plan: str, start: date) -> list[tuple[int, int, date]]:
    """Return ``(sequence, amount, due_date)`` rows of equal monthly installments.

    Any rounding remainder is added to the first installment so the rows sum to
    exactly ``fee``.
    """
    count = installment_count(plan)
    base = fee // count
    remainder = fee - base * count
    return [
        (index + 1, base + (remainder if index == 0 else 0), add_months(start, index))
        for index in range(count)
    ]


def allocate(total_paid: int, installments: Iterable[Installment]) -> None:
    """Spread a total collected amount across installments, oldest first."""
    remaining = total_paid
    for installment in sorted(installments, key=lambda item: item.sequence):
        covered = min(installment.amount, max(remaining, 0))
        installment.paid_amount = covered
        remaining -= covered


def next_due_date(installments: Iterable[Installment]) -> date | None:
    """Earliest due date among installments that are not fully paid."""
    unpaid = [i for i in installments if (i.paid_amount or 0) < i.amount]
    return min((i.due_date for i in unpaid), default=None)
