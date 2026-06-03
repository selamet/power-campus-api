"""User account model and role enumeration."""

import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import AuditedBase


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
