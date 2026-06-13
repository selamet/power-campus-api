"""Staff management endpoints used by the admin panel."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apps.users.models import User
from app.apps.users.permissions import PERMISSION_CATALOG, Permission
from app.apps.users.schemas import (
    CreateStaffRequest,
    PermissionGroupOut,
    StaffOut,
    UpdateStaffRequest,
)
from app.apps.users.service import (
    EmailAlreadyExistsError,
    InvalidPermissionError,
    InvalidRoleError,
    SelfLockoutError,
    StaffNotFoundError,
    UserService,
)
from app.core.deps import SessionDep, require_permission

router = APIRouter(prefix="/users", tags=["users"])

CanRead = Annotated[User, Depends(require_permission(Permission.users_read))]
CanWrite = Annotated[User, Depends(require_permission(Permission.users_write))]

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı."
)


def _to_staff_out(user: User) -> StaffOut:
    return StaffOut(
        id=user.id,
        name=user.full_name,
        email=user.email,
        role=user.role,
        branch=user.branch,
        is_active=user.is_active,
        permissions=sorted(user.effective_permissions()),
        must_change_password=user.must_change_password,
    )


@router.get("/permissions/catalog", response_model=list[PermissionGroupOut])
async def permission_catalog(_: CanRead) -> list[PermissionGroupOut]:
    """Modules and their grantable permissions, for rendering the editor."""
    return [
        PermissionGroupOut(
            module=group.module,
            label=group.label,
            permissions=[item.__dict__ for item in group.permissions],
        )
        for group in PERMISSION_CATALOG
    ]


@router.get("", response_model=list[StaffOut])
async def list_staff(session: SessionDep, _: CanRead) -> list[StaffOut]:
    staff = await UserService(session).list_staff()
    return [_to_staff_out(user) for user in staff]


@router.post("", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: CreateStaffRequest, session: SessionDep, _: CanWrite
) -> StaffOut:
    try:
        user = await UserService(session).create_staff(payload)
    except (EmailAlreadyExistsError, InvalidPermissionError, InvalidRoleError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    return _to_staff_out(user)


@router.patch("/{user_id}", response_model=StaffOut)
async def update_staff(
    user_id: int, payload: UpdateStaffRequest, session: SessionDep, actor: CanWrite
) -> StaffOut:
    try:
        user = await UserService(session).update_staff(user_id, payload, acting_user=actor)
    except StaffNotFoundError:
        raise _NOT_FOUND from None
    except (InvalidPermissionError, InvalidRoleError, SelfLockoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    return _to_staff_out(user)
