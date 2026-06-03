"""Authentication use cases."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole
from app.apps.users.repository import UserRepository
from app.core.security import create_access_token, verify_password

# Roles permitted to sign in to the management panel for now.
LOGIN_ALLOWED_ROLES = frozenset({UserRole.admin, UserRole.manager})


class AuthError(Exception):
    """Raised when authentication fails; carries a user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def login(self, email: str, password: str) -> tuple[User, str]:
        """Validate credentials and return the user plus a fresh access token."""
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("E-posta veya parola hatalı.")
        if not user.is_active:
            raise AuthError("Hesabınız pasif durumda.")
        if user.role not in LOGIN_ALLOWED_ROLES:
            raise AuthError("Bu hesabın panele giriş yetkisi yok.")
        return user, create_access_token(user.id)
