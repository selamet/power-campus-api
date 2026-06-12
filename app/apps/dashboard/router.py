"""Dashboard endpoints (authenticated read-only aggregates)."""

from fastapi import APIRouter

from app.apps.dashboard.schemas import ActivityItem, DashboardStats, MonthlyPoint, OverdueItem
from app.apps.dashboard.service import DashboardService
from app.core.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(session: SessionDep, _: CurrentUser) -> DashboardStats:
    return await DashboardService(session).stats()


@router.get("/activity", response_model=list[ActivityItem])
async def get_activity(session: SessionDep, _: CurrentUser) -> list[ActivityItem]:
    return await DashboardService(session).activity()


@router.get("/overdue", response_model=list[OverdueItem])
async def get_overdue(session: SessionDep, _: CurrentUser) -> list[OverdueItem]:
    return await DashboardService(session).overdue()


@router.get("/monthly", response_model=list[MonthlyPoint])
async def get_monthly(session: SessionDep, _: CurrentUser) -> list[MonthlyPoint]:
    return await DashboardService(session).monthly()
