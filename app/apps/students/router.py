"""Student endpoints consumed by the dashboard and students page."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.apps.students.schemas import NewStudentInput, StudentOut, StudentUpdate
from app.apps.students.service import StudentNotFoundError, StudentService
from app.apps.users.models import User, UserRole
from app.core.deps import CurrentUser, SessionDep, require_roles

router = APIRouter(prefix="/students", tags=["students"])

# Creating, approving and rejecting students is restricted to staff.
AdminOrManager = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")


@router.get("", response_model=list[StudentOut])
async def list_students(session: SessionDep, _: CurrentUser) -> list[StudentOut]:
    return await StudentService(session).list_students()


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: NewStudentInput, session: SessionDep, _: AdminOrManager
) -> StudentOut:
    return await StudentService(session).create_student(payload)


@router.patch("/{code}", response_model=StudentOut)
async def update_student(
    code: str, payload: StudentUpdate, session: SessionDep, _: AdminOrManager
) -> StudentOut:
    try:
        return await StudentService(session).update_student(code, payload)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.patch("/{code}/approve", response_model=StudentOut)
async def approve_student(code: str, session: SessionDep, _: AdminOrManager) -> StudentOut:
    try:
        return await StudentService(session).approve_student(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.patch("/{code}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_student(code: str, session: SessionDep, _: AdminOrManager) -> Response:
    try:
        await StudentService(session).reject_student(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
