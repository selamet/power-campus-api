"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.apps.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    StaffOut,
)
from app.apps.auth.service import AuthError, AuthService
from app.apps.users.models import User
from app.core.deps import CurrentUser, SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_staff(user: User) -> StaffOut:
    return StaffOut(
        name=user.full_name,
        role=user.role,
        email=user.email,
        branch=user.branch,
        permissions=sorted(user.effective_permissions()),
        must_change_password=user.must_change_password,
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session: SessionDep) -> LoginResponse:
    try:
        user, token = await AuthService(session).login(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        ) from exc
    return LoginResponse(user=_to_staff(user), token=token)


@router.get("/me", response_model=StaffOut)
async def me(user: CurrentUser) -> StaffOut:
    return _to_staff(user)


@router.post("/password", response_model=StaffOut)
async def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, session: SessionDep
) -> StaffOut:
    try:
        updated = await AuthService(session).change_password(
            user, payload.current_password, payload.new_password
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return _to_staff(updated)
