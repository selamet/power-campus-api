"""Ders programı (schedule) endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.apps.schedule.schemas import (
    ApplyResult,
    GeneratePreview,
    RuleTemplateCreate,
    RuleTemplateOut,
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    SessionCreate,
    SessionLock,
    SessionMove,
    SessionOut,
    TermSettingsOut,
    TermSettingsUpdate,
)
from app.apps.schedule.service import ConflictError, ScheduleService
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


@router.post("/classes/{class_id}/schedule/generate", response_model=GeneratePreview)
async def generate_class(class_id: int, session: SessionDep, _: CanWrite) -> GeneratePreview:
    return await ScheduleService(session).generate_for_class(class_id)


@router.post("/terms/{term_id}/schedule/generate", response_model=GeneratePreview)
async def generate_term(term_id: int, session: SessionDep, _: CanWrite) -> GeneratePreview:
    return await ScheduleService(session).generate_for_term(term_id)


@router.post("/classes/{class_id}/schedule/apply", response_model=ApplyResult)
async def apply_class(class_id: int, session: SessionDep, _: CanWrite) -> ApplyResult:
    return await ScheduleService(session).apply_for_class(class_id)


@router.post("/terms/{term_id}/schedule/apply", response_model=ApplyResult)
async def apply_term(term_id: int, session: SessionDep, _: CanWrite) -> ApplyResult:
    return await ScheduleService(session).apply_for_term(term_id)


@router.post(
    "/schedule/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED
)
async def add_session(payload: SessionCreate, session: SessionDep, _: CanWrite) -> SessionOut:
    try:
        return await ScheduleService(session).add_session(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.patch("/schedule/sessions/{session_id}", response_model=SessionOut)
async def move_session(
    session_id: int, payload: SessionMove, session: SessionDep, _: CanWrite
) -> SessionOut:
    try:
        return await ScheduleService(session).move_session(session_id, payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.delete("/schedule/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, session: SessionDep, _: CanWrite) -> Response:
    try:
        await ScheduleService(session).delete_session(session_id)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/schedule/sessions/{session_id}/lock", response_model=SessionOut)
async def lock_session(
    session_id: int, payload: SessionLock, session: SessionDep, _: CanWrite
) -> SessionOut:
    try:
        return await ScheduleService(session).set_lock(session_id, payload.locked)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.get("/schedule/rule-templates", response_model=list[RuleTemplateOut])
async def list_rule_templates(session: SessionDep, _: CanRead) -> list[RuleTemplateOut]:
    return await ScheduleService(session).list_rule_templates()


@router.post(
    "/schedule/rule-templates", response_model=RuleTemplateOut, status_code=status.HTTP_201_CREATED
)
async def create_rule_template(
    payload: RuleTemplateCreate, session: SessionDep, _: CanWrite
) -> RuleTemplateOut:
    try:
        return await ScheduleService(session).create_rule_template(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc


@router.delete(
    "/schedule/rule-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_rule_template(template_id: int, session: SessionDep, _: CanWrite) -> Response:
    await ScheduleService(session).delete_rule_template(template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
