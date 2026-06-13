"""Installment and payment endpoints, nested under a student."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.apps.payments.schemas import InstallmentOut, PaymentOut, RecordPaymentRequest
from app.apps.payments.service import PaymentService
from app.apps.students.schemas import StudentOut
from app.apps.students.service import StudentNotFoundError
from app.apps.users.models import User
from app.apps.users.permissions import Permission
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/students", tags=["payments"])

CanRead = Annotated[User, Depends(require_permission(Permission.finance_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.finance_write))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Öğrenci bulunamadı.")


@router.get("/{code}/installments", response_model=list[InstallmentOut])
async def list_installments(code: str, session: SessionDep, _: CanRead) -> list[InstallmentOut]:
    try:
        return await PaymentService(session).list_installments(code)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.get("/{code}/payments", response_model=list[PaymentOut])
async def list_payments(
    code: str,
    session: SessionDep,
    _: CanRead,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaymentOut]:
    try:
        return await PaymentService(session).list_payments(code, limit=limit, offset=offset)
    except StudentNotFoundError:
        raise _NOT_FOUND from None


@router.post("/{code}/payments", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def record_payment(
    code: str, payload: RecordPaymentRequest, session: SessionDep, _: CanWrite
) -> StudentOut:
    try:
        return await PaymentService(session).record_payment(code, payload)
    except StudentNotFoundError:
        raise _NOT_FOUND from None
