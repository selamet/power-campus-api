"""Dashboard endpoints (authenticated read-only aggregates)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.apps.dashboard.schemas import ActivityItem, DashboardStats, MonthlyPoint, OverdueItem
from app.apps.dashboard.service import DashboardService
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

CanRead = Annotated[User, Depends(require_permission(Permission.dashboard_read))]


@router.get("/stats", response_model=DashboardStats)
async def get_stats(session: SessionDep, _: CanRead) -> DashboardStats:
    return await DashboardService(session).stats()


@router.get("/activity", response_model=list[ActivityItem])
async def get_activity(session: SessionDep, _: CanRead) -> list[ActivityItem]:
    return await DashboardService(session).activity()


@router.get("/overdue", response_model=list[OverdueItem])
async def get_overdue(session: SessionDep, _: CanRead) -> list[OverdueItem]:
    return await DashboardService(session).overdue()


@router.get("/monthly", response_model=list[MonthlyPoint])
async def get_monthly(session: SessionDep, _: CanRead) -> list[MonthlyPoint]:
    return await DashboardService(session).monthly()
