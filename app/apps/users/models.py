"""User account model, role enumeration and per-user permissions."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.apps.users.permissions import ALL_PERMISSIONS
from app.core.base import AuditedBase, Base


class UserRole(enum.StrEnum):
    """System roles. Only ``admin`` and ``manager`` can authenticate for now."""

    admin = "admin"
    manager = "manager"
    teacher = "teacher"
    student = "student"


class User(AuditedBase):
    """An account that can sign in and manage the platform."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("passwordHash", String(255), nullable=False)
    full_name: Mapped[str] = mapped_column("fullName", String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="userRole",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "isActive", Boolean, server_default="1", nullable=False
    )

    permissions: Mapped[list["UserPermission"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def permission_keys(self) -> set[str]:
        """Permission strings explicitly granted to this account."""
        return {grant.permission for grant in self.permissions}

    def effective_permissions(self) -> frozenset[str]:
        """Permissions this account actually holds (``admin`` holds them all)."""
        if self.role is UserRole.admin:
            return ALL_PERMISSIONS
        return frozenset(self.permission_keys)

    def has_permission(self, permission: str) -> bool:
        return self.role is UserRole.admin or permission in self.permission_keys


class UserPermission(Base):
    """A single permission granted to a user account."""

    __tablename__ = "userPermissions"

    user_id: Mapped[int] = mapped_column(
        "userId",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission: Mapped[str] = mapped_column(String(64), primary_key=True)

    user: Mapped[User] = relationship(back_populates="permissions")
