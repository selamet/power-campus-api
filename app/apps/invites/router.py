"""Invite endpoints: staff link creation and the public welcome flow."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apps.invites.models import Invite
from app.apps.invites.schemas import (
    CreateInviteRequest,
    InviteOut,
    InvitePublicOut,
    WelcomeSubmitRequest,
    WelcomeSubmitResponse,
)
from app.apps.invites.service import (
    InviteAlreadyCompletedError,
    InviteNotFoundError,
    InviteService,
)
from app.apps.users.models import User, UserRole
from app.core.deps import SessionDep, require_roles

router = APIRouter(prefix="/invites", tags=["invites"])

AdminOrManager = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Davet bulunamadı.")


def _to_invite_out(invite: Invite) -> InviteOut:
    return InviteOut(
        tckn=invite.tckn,
        name=invite.name,
        lang=invite.lang,
        course=invite.course,
        status=invite.status,
        path=f"/hosgeldin/{invite.tckn}",
    )


@router.post("", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: CreateInviteRequest, session: SessionDep, _: AdminOrManager
) -> InviteOut:
    invite = await InviteService(session).create_invite(payload)
    return _to_invite_out(invite)


@router.get("/{tckn}", response_model=InvitePublicOut)
async def get_invite(tckn: str, session: SessionDep) -> Invite:
    """Public: the welcome form fetches its pre-filled data."""
    try:
        return await InviteService(session).get_invite(tckn)
    except InviteNotFoundError:
        raise _NOT_FOUND from None


@router.post(
    "/{tckn}/submit",
    response_model=WelcomeSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_welcome(
    tckn: str, payload: WelcomeSubmitRequest, session: SessionDep
) -> WelcomeSubmitResponse:
    """Public: the student submits their welcome form."""
    try:
        student = await InviteService(session).submit_welcome(tckn, payload)
    except InviteNotFoundError:
        raise _NOT_FOUND from None
    except InviteAlreadyCompletedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu form daha önce gönderilmiş.",
        ) from None
    enrollment_status = student.enrollments[-1].status
    return WelcomeSubmitResponse(student_code=student.student_code, status=enrollment_status)
