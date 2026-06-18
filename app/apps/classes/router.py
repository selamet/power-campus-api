"""Class (section) management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.apps.classes.lesson_service import LessonNotFoundError, LessonService
from app.apps.classes.lessons import (
    LESSON_LABELS,
    LessonType,
)
from app.apps.classes.schemas import (
    AssignCriteria,
    AssignStudentsRequest,
    ClassLessonOut,
    ClassOut,
    ClassStudentOut,
    ClassUpdate,
    CreateClassRequest,
    LessonInput,
    LessonTypeOut,
    LessonUpdate,
)
from app.apps.classes.service import (
    ClassNotFoundError,
    ClassService,
    DuplicateClassError,
    InactiveTeacherError,
    TeacherNotFoundError,
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
_LESSON_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Ders bulunamadı."
)
_TEACHER_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Öğretmen bulunamadı."
)
_INACTIVE_TEACHER = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Pasif bir öğretmen derse atanamaz.",
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
    except TeacherNotFoundError:
        raise _TEACHER_NOT_FOUND from None
    except InactiveTeacherError:
        raise _INACTIVE_TEACHER from None


@router.patch("/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: int, payload: ClassUpdate, session: SessionDep, _: CanWrite
) -> ClassOut:
    try:
        return await ClassService(session).update_class(class_id, payload)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    except TeacherNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Öğretmen bulunamadı."
        ) from None
    except InactiveTeacherError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pasif bir öğretmen sınıfa atanamaz.",
        ) from None
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
async def auto_assign(
    class_id: int,
    session: SessionDep,
    _: CanWrite,
    criteria: AssignCriteria | None = None,
) -> list[ClassStudentOut]:
    try:
        return await ClassService(session).auto_assign(class_id, criteria)
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


@router.get("/lesson-types", response_model=list[LessonTypeOut])
async def lesson_types(session: SessionDep, _: CanRead) -> list[LessonTypeOut]:
    return [
        LessonTypeOut(
            value=lesson_type,
            label=LESSON_LABELS[lesson_type],
        )
        for lesson_type in LessonType
    ]


@router.get("/{class_id}/lessons", response_model=list[ClassLessonOut])
async def list_lessons(class_id: int, session: SessionDep, _: CanRead) -> list[ClassLessonOut]:
    try:
        return await LessonService(session).list_lessons(class_id)
    except ClassNotFoundError:
        raise _NOT_FOUND from None


@router.post(
    "/{class_id}/lessons", response_model=ClassLessonOut, status_code=status.HTTP_201_CREATED
)
async def add_lesson(
    class_id: int, payload: LessonInput, session: SessionDep, _: CanWrite
) -> ClassLessonOut:
    try:
        return await LessonService(session).add_lesson(class_id, payload)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    except TeacherNotFoundError:
        raise _TEACHER_NOT_FOUND from None
    except InactiveTeacherError:
        raise _INACTIVE_TEACHER from None


@router.patch("/{class_id}/lessons/{lesson_id}", response_model=ClassLessonOut)
async def update_lesson(
    class_id: int, lesson_id: int, payload: LessonUpdate, session: SessionDep, _: CanWrite
) -> ClassLessonOut:
    try:
        return await LessonService(session).update_lesson(class_id, lesson_id, payload)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    except LessonNotFoundError:
        raise _LESSON_NOT_FOUND from None
    except TeacherNotFoundError:
        raise _TEACHER_NOT_FOUND from None
    except InactiveTeacherError:
        raise _INACTIVE_TEACHER from None


@router.delete("/{class_id}/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    class_id: int, lesson_id: int, session: SessionDep, _: CanWrite
) -> Response:
    try:
        await LessonService(session).delete_lesson(class_id, lesson_id)
    except ClassNotFoundError:
        raise _NOT_FOUND from None
    except LessonNotFoundError:
        raise _LESSON_NOT_FOUND from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
