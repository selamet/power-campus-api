"""Common FastAPI dependencies: database session and authentication."""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole
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
