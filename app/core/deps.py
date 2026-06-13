"""Common FastAPI dependencies: database session and authentication."""

from collections.abc import Awaitable, Callable
from datetime import UTC
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole
from app.apps.users.permissions import Permission
from app.apps.users.repository import UserRepository
from app.core.context import current_user_id
from app.core.db import get_session
from app.core.security import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=True)

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Geçersiz veya süresi dolmuş oturum.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    session: SessionDep,
) -> User:
    """Resolve the authenticated user from the bearer token.

    Also records the user id in the request context so the audit hook can
    attribute ``createdBy`` / ``updatedBy``.
    """
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _credentials_error from None

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _credentials_error

    # Reject tokens issued before the password last changed (compared at the
    # token's second-level ``iat`` precision), so a reset invalidates old
    # sessions while the freshly issued token stays valid.
    changed_at = user.password_changed_at
    if changed_at is not None:
        if changed_at.tzinfo is None:
            changed_at = changed_at.replace(tzinfo=UTC)
        if int(payload.get("iat", 0)) < int(changed_at.timestamp()):
            raise _credentials_error

    current_user_id.set(user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that allows only the given roles."""

    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz yok.",
            )
        return user

    return dependency


def require_permission(*permissions: Permission) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that requires every given permission.

    ``admin`` accounts hold all permissions implicitly and always pass.

    Also enforces the first-login password reset at the API layer: a user who
    still owes a password change is blocked from every protected resource (only
    ``/auth/me`` and ``/auth/password`` stay reachable, since they don't use this
    dependency), so the forced reset can't be bypassed with a direct API call.
    """

    async def dependency(user: CurrentUser) -> User:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Devam etmeden önce parolanızı yenilemeniz gerekiyor.",
            )
        if not all(user.has_permission(permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz yok.",
            )
        return user

    return dependency
