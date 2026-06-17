"""Teacher management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apps.teachers.models import TeacherStatus
from app.apps.teachers.schemas import TeacherCreate, TeacherOut, TeacherUpdate
from app.apps.teachers.service import TeacherNotFoundError, TeacherService
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/teachers", tags=["teachers"])

CanRead = Annotated[User, Depends(require_permission(Permission.teachers_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.teachers_write))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğretmen bulunamadı.")


@router.get("", response_model=list[TeacherOut])
async def list_teachers(
    session: SessionDep, _: CanRead, status: TeacherStatus | None = None
) -> list[TeacherOut]:
    return await TeacherService(session).list_teachers(status=status)


@router.post("", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
async def create_teacher(payload: TeacherCreate, session: SessionDep, _: CanWrite) -> TeacherOut:
    return await TeacherService(session).create_teacher(payload)


@router.get("/{teacher_id}", response_model=TeacherOut)
async def get_teacher(teacher_id: int, session: SessionDep, _: CanRead) -> TeacherOut:
    try:
        return await TeacherService(session).get_teacher(teacher_id)
    except TeacherNotFoundError:
        raise _NOT_FOUND from None


@router.patch("/{teacher_id}", response_model=TeacherOut)
async def update_teacher(
    teacher_id: int, payload: TeacherUpdate, session: SessionDep, _: CanWrite
) -> TeacherOut:
    try:
        return await TeacherService(session).update_teacher(teacher_id, payload)
    except TeacherNotFoundError:
        raise _NOT_FOUND from None
