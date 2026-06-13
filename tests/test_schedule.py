"""Unit tests for the pure installment-scheduling helpers."""

from datetime import date

from app.apps.payments.models import Installment
from app.apps.payments.schedule import (
    add_months,
    allocate,
    build_schedule,
    installment_count,
    next_due_date,
)


def test_installment_count_parses_plan_label() -> None:
    assert installment_count("Peşin") == 1
    assert installment_count("3 Taksit") == 3
    assert installment_count("12 Taksit") == 12
    assert installment_count("") == 1


def test_add_months_clamps_to_end_of_month() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert add_months(date(2026, 1, 31), 13) == date(2027, 2, 28)


def test_build_schedule_sums_to_fee_with_remainder_on_first() -> None:
    rows = build_schedule(10_000, "3 Taksit", date(2026, 1, 1))
    amounts = [amount for _, amount, _ in rows]
    due_dates = [due for _, _, due in rows]

    assert sum(amounts) == 10_000
    assert amounts == [3334, 3333, 3333]
    assert due_dates == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]


def test_build_schedule_single_installment_for_pesin() -> None:
    rows = build_schedule(18_500, "Peşin", date(2026, 2, 3))
    assert rows == [(1, 18_500, date(2026, 2, 3))]


def _installments(amounts: list[int]) -> list[Installment]:
    return [
        Installment(sequence=i + 1, amount=amount, paid_amount=0, due_date=date(2026, i + 1, 1))
        for i, amount in enumerate(amounts)
    ]


def test_allocate_fills_oldest_first() -> None:
    items = _installments([100, 100, 100])
    allocate(150, items)
    assert [item.paid_amount for item in items] == [100, 50, 0]


def test_allocate_caps_each_installment() -> None:
    items = _installments([100, 100])
    allocate(500, items)
    assert [item.paid_amount for item in items] == [100, 100]


def test_next_due_date_returns_first_unpaid() -> None:
    items = _installments([100, 100, 100])
    items[0].paid_amount = 100
    assert next_due_date(items) == date(2026, 2, 1)


def test_next_due_date_none_when_all_paid() -> None:
    items = _installments([100, 100])
    for item in items:
        item.paid_amount = item.amount
    assert next_due_date(items) is None
