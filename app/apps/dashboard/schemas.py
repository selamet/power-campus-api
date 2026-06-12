"""Dashboard read-model schemas."""

from datetime import date

from app.core.schemas import CamelModel


class DashboardStats(CamelModel):
    total_students: int
    active_students: int
    pending_approvals: int
    total_collected: int
    outstanding: int
    due_today: int
    overdue_count: int
    overdue_total: int
    invites_pending: int
    invites_completed: int


class ActivityItem(CamelModel):
    who: str
    what: str
    icon: str
    kind: str  # "accent" | "neutral" | "ok"
    time: str  # human-readable relative time, e.g. "12 dk önce"


class OverdueItem(CamelModel):
    """An unpaid installment whose due date has passed."""

    student_id: str  # public student code, e.g. "PA-1042"
    name: str
    sequence: int
    due_date: date
    amount: int  # remaining amount on this installment


class MonthlyPoint(CamelModel):
    """Expected vs collected totals for one calendar month."""

    month: str  # "2026-01"
    label: str  # short Turkish month name, e.g. "Oca"
    expected: int
    collected: int
