"""Class (section) management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.apps.classes.schemas import (
    AssignStudentsRequest,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    CreateClassRequest,
)
from app.apps.classes.service import (
    ClassNotFoundError,
    ClassService,
    DuplicateClassError,
    TermNotFoundError,
)
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/classes", tags=["classes"])

CanRead = Annotated[User, Depends(require_permission(Permission.classes_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.classes_write))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sınıf bulunamadı.")
_DUPLICATE = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Bu dönemde aynı seviye ve şubeden bir sınıf zaten var.",
)


@router.get("", response_model=list[ClassOut])
async def list_classes(
    session: SessionDep, _: CanRead, term_id: int | None = None
) -> list[ClassOut]:
    return await ClassService(session).list_classes(term_id=term_id)


@router.post("", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(payload: CreateClassRequest, session: SessionDep, _: CanWrite) -> ClassOut:
    try:
        return await ClassService(session).create_class(payload)
    except TermNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı."
        ) from None
    except DuplicateClassError:
        raise _DUPLICATE from None


@router.patch("/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: int, payload: ClassUpdate, session: SessionDep, _: CanWrite
) -> ClassOut:
    try:
        return await ClassService(session).update_class(class_id, payload)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    except DuplicateClassError:
        raise _DUPLICATE from None


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(class_id: int, session: SessionDep, _: CanWrite) -> Response:
    try:
        await ClassService(session).delete_class(class_id)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{class_id}/students", response_model=list[ClassStudentOut])
async def list_class_students(
    class_id: int, session: SessionDep, _: CanRead
) -> list[ClassStudentOut]:
    return await ClassService(session).list_class_students(class_id)


@router.post(
    "/{class_id}/students",
    response_model=list[ClassStudentOut],
    status_code=status.HTTP_201_CREATED,
)
async def assign_students(
    class_id: int, payload: AssignStudentsRequest, session: SessionDep, _: CanWrite
) -> list[ClassStudentOut]:
    try:
        return await ClassService(session).assign_students(class_id, payload)
    except ClassNotFoundError:
        raise _NOT_FOUND from None


@router.post("/{class_id}/auto-assign", response_model=list[ClassStudentOut])
async def auto_assign(class_id: int, session: SessionDep, _: CanWrite) -> list[ClassStudentOut]:
    try:
        return await ClassService(session).auto_assign(class_id)
    except ClassNotFoundError:
        raise _NOT_FOUND from None


@router.delete("/{class_id}/students/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_student(
    class_id: int, code: str, session: SessionDep, _: CanWrite
) -> Response:
    try:
        await ClassService(session).unassign_student(class_id, code)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
