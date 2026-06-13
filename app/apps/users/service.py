"""Use cases for managing staff accounts and their permissions."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.users.models import User, UserPermission, UserRole
from app.apps.users.permissions import ALL_PERMISSIONS
from app.apps.users.repository import UserRepository
from app.apps.users.schemas import CreateStaffRequest, UpdateStaffRequest
from app.core.security import hash_password


class StaffError(Exception):
    """Base for staff-management failures; carries a user-facing message."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class StaffNotFoundError(StaffError):
    def __init__(self) -> None:
        super().__init__("Kullanıcı bulunamadı.")


class EmailAlreadyExistsError(StaffError):
    def __init__(self) -> None:
        super().__init__("Bu e-posta ile bir hesap zaten var.")


class InvalidPermissionError(StaffError):
    def __init__(self) -> None:
        super().__init__("Tanımsız bir izin gönderildi.")


class InvalidRoleError(StaffError):
    def __init__(self) -> None:
        super().__init__("Bu rol panel kullanıcısına atanamaz.")


class SelfLockoutError(StaffError):
    def __init__(self) -> None:
        super().__init__("Kendi hesabınızın erişimini kısıtlayamazsınız.")


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def list_staff(self) -> list[User]:
        return await self._users.list_staff()

    async def create_staff(self, payload: CreateStaffRequest) -> User:
        self._guard_role(payload.role)
        permissions = self._validated_permissions(payload.permissions)
        if await self._users.get_by_email(payload.email) is not None:
            raise EmailAlreadyExistsError
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.name,
            role=payload.role,
            branch=payload.branch,
            permissions=[UserPermission(permission=key) for key in permissions],
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update_staff(
        self, user_id: int, payload: UpdateStaffRequest, *, acting_user: User
    ) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None or user.role is UserRole.student:
            raise StaffNotFoundError

        if payload.role is not None:
            self._guard_role(payload.role)
        self._guard_self_lockout(user, payload, acting_user)

        if payload.name is not None:
            user.full_name = payload.name
        if payload.role is not None:
            user.role = payload.role
        if payload.branch is not None:
            user.branch = payload.branch
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.password:
            user.password_hash = hash_password(payload.password)
        if payload.permissions is not None:
            keys = self._validated_permissions(payload.permissions)
            user.permissions = [UserPermission(permission=key) for key in keys]

        await self._session.commit()
        await self._session.refresh(user)
        return user

    @staticmethod
    def _guard_role(role: UserRole) -> None:
        if role is UserRole.student:
            raise InvalidRoleError

    @staticmethod
    def _validated_permissions(permissions: list[str]) -> list[str]:
        unique = sorted(set(permissions))
        if any(key not in ALL_PERMISSIONS for key in unique):
            raise InvalidPermissionError
        return unique

    @staticmethod
    def _guard_self_lockout(
        user: User, payload: UpdateStaffRequest, acting_user: User
    ) -> None:
        """Stop an admin from locking themselves out of the panel."""
        if user.id != acting_user.id:
            return
        if payload.is_active is False:
            raise SelfLockoutError
        if payload.role is not None and payload.role is not user.role:
            raise SelfLockoutError
