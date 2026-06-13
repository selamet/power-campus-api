"""Term (semester) management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apps.terms.schemas import CreateTermRequest, TermOut, TermUpdate
from app.apps.terms.service import InvalidTermDatesError, TermNotFoundError, TermService
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/terms", tags=["terms"])

CanRead = Annotated[User, Depends(require_permission(Permission.terms_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.terms_write))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dönem bulunamadı.")


@router.get("", response_model=list[TermOut])
async def list_terms(session: SessionDep, _: CanRead) -> list[TermOut]:
    return await TermService(session).list_terms()


@router.post("", response_model=TermOut, status_code=status.HTTP_201_CREATED)
async def create_term(payload: CreateTermRequest, session: SessionDep, _: CanWrite) -> TermOut:
    try:
        return await TermService(session).create_term(payload)
    except InvalidTermDatesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc


@router.patch("/{term_id}", response_model=TermOut)
async def update_term(
    term_id: int, payload: TermUpdate, session: SessionDep, _: CanWrite
) -> TermOut:
    try:
        return await TermService(session).update_term(term_id, payload)
    except TermNotFoundError:
        raise _NOT_FOUND from None
    except InvalidTermDatesError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
