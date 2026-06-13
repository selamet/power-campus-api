"""Student endpoints consumed by the dashboard and students page."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.apps.students.schemas import (
    EnrollmentOut,
    NewEnrollmentInput,
    NewStudentInput,
    StudentOut,
    StudentUpdate,
)
from app.apps.students.service import (
    DuplicateTcknError,
    DuplicateTermEnrollmentError,
    PaymentPlanMissingError,
    StudentNotFoundError,
    StudentService,
)
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/students", tags=["students"])

CanRead = Annotated[User, Depends(require_permission(Permission.students_read))]
# Creating, approving and rejecting students requires write access.
CanWrite = Annotated[User, Depends(require_permission(Permission.students_write))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")


@router.get("", response_model=list[StudentOut])
async def list_students(
    session: SessionDep,
    _: CanRead,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StudentOut]:
    """List students. Without ``limit`` the full list is returned (current
    frontend behaviour); pass ``limit``/``offset`` to page through results."""
    return await StudentService(session).list_students(limit=limit, offset=offset)


@router.get("/{identifier}", response_model=StudentOut)
async def get_student(identifier: str, session: SessionDep, _: CanRead) -> StudentOut:
    """Fetch one student by TCKN, falling back to the public code (``PA-…``)."""
    try:
        return await StudentService(session).get_student(identifier)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: NewStudentInput, session: SessionDep, _: CanWrite
) -> StudentOut:
    return await StudentService(session).create_student(payload)


@router.patch("/{code}", response_model=StudentOut)
async def update_student(
    code: str, payload: StudentUpdate, session: SessionDep, _: CanWrite
) -> StudentOut:
    try:
        return await StudentService(session).update_student(code, payload)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
    except DuplicateTcknError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu kimlik numarası (TCKN/pasaport) başka bir öğrencide kayıtlı.",
        ) from None


@router.patch("/{code}/approve", response_model=StudentOut)
async def approve_student(code: str, session: SessionDep, user: CanWrite) -> StudentOut:
    try:
        return await StudentService(session).approve_student(code, user)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
    except PaymentPlanMissingError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ödeme planı tanımlanmadan kayıt onaylanamaz.",
        ) from None


@router.patch("/{code}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_student(code: str, session: SessionDep, _: CanWrite) -> Response:
    try:
        await StudentService(session).reject_student(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{code}/enrollments", response_model=list[EnrollmentOut])
async def list_enrollments(code: str, session: SessionDep, _: CanRead) -> list[EnrollmentOut]:
    """Every term registration of the student, newest first."""
    try:
        return await StudentService(session).list_enrollments(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.post(
    "/{code}/enrollments", response_model=StudentOut, status_code=status.HTTP_201_CREATED
)
async def add_enrollment(
    code: str, payload: NewEnrollmentInput, session: SessionDep, user: CanWrite
) -> StudentOut:
    """Enroll an existing student into another term (a new active enrollment)."""
    try:
        return await StudentService(session).add_enrollment(code, payload, user)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
    except DuplicateTermEnrollmentError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Öğrenci bu döneme zaten kayıtlı.",
        ) from None
