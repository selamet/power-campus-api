"""Authentication use cases."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserRole
from app.apps.users.repository import UserRepository
from app.core.security import create_access_token, hash_password, verify_password

# Roles permitted to sign in to the management panel for now.
LOGIN_ALLOWED_ROLES = frozenset({UserRole.admin, UserRole.manager})


class AuthError(Exception):
    """Raised when authentication fails; carries a user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
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

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> tuple[User, str]:
        """Set a new password after verifying the current one.

        Clears the ``must_change_password`` flag, stamps ``password_changed_at``
        (which invalidates tokens issued earlier) and returns a fresh token so
        the caller's own session survives the change.
        """
        if not verify_password(current_password, user.password_hash):
            raise AuthError("Mevcut parola hatalı.")
        if verify_password(new_password, user.password_hash):
            raise AuthError("Yeni parola mevcut parolayla aynı olamaz.")
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(user)
        return user, create_access_token(user.id)
