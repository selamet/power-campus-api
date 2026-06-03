"""Dashboard read-model schemas."""

from app.core.schemas import CamelModel


class DashboardStats(CamelModel):
    total_students: int
    active_students: int
    pending_approvals: int
    total_collected: int
    outstanding: int


class ActivityItem(CamelModel):
    who: str
    what: str
    icon: str
    kind: str  # "accent" | "neutral" | "ok"
    time: str  # human-readable relative time, e.g. "12 dk önce"
