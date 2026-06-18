"""Ders programı (schedule) endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.apps.schedule.schemas import (
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    SessionOut,
    TermSettingsOut,
    TermSettingsUpdate,
)
from app.apps.schedule.service import ScheduleService
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(tags=["schedule"])

CanRead = Annotated[User, Depends(require_permission(Permission.schedule_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.schedule_write))]


@router.get("/terms/{term_id}/schedule/settings", response_model=TermSettingsOut)
async def get_settings(term_id: int, session: SessionDep, _: CanRead) -> TermSettingsOut:
    return await ScheduleService(session).get_settings(term_id)


@router.put("/terms/{term_id}/schedule/settings", response_model=TermSettingsOut)
async def put_settings(
    term_id: int, payload: TermSettingsUpdate, session: SessionDep, _: CanWrite
) -> TermSettingsOut:
    return await ScheduleService(session).upsert_settings(term_id, payload)


@router.get("/classes/{class_id}/schedule/config", response_model=ScheduleConfigOut)
async def get_config(class_id: int, session: SessionDep, _: CanRead) -> ScheduleConfigOut:
    return await ScheduleService(session).get_config(class_id)


@router.put("/classes/{class_id}/schedule/config", response_model=ScheduleConfigOut)
async def put_config(
    class_id: int, payload: ScheduleConfigUpdate, session: SessionDep, _: CanWrite
) -> ScheduleConfigOut:
    return await ScheduleService(session).upsert_config(class_id, payload)


@router.get("/classes/{class_id}/schedule", response_model=list[SessionOut])
async def class_schedule(class_id: int, session: SessionDep, _: CanRead) -> list[SessionOut]:
    return await ScheduleService(session).class_schedule(class_id)


@router.get("/teachers/{teacher_id}/schedule", response_model=list[SessionOut])
async def teacher_schedule(teacher_id: int, session: SessionDep, _: CanRead) -> list[SessionOut]:
    return await ScheduleService(session).teacher_schedule(teacher_id)


@router.get("/terms/{term_id}/schedule", response_model=list[SessionOut])
async def term_schedule(
    term_id: int, session: SessionDep, _: CanRead, weekday: int | None = None
) -> list[SessionOut]:
    return await ScheduleService(session).term_schedule(term_id, weekday)
