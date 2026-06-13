"""Request/response schemas for staff account management."""

from pydantic import EmailStr, Field

from app.apps.users.models import UserRole
from app.core.schemas import CamelModel


class StaffOut(CamelModel):
    """A staff account as listed and edited in the admin panel."""

    id: int
    name: str
    email: EmailStr
    role: UserRole
    branch: str | None = None
    is_active: bool
    permissions: list[str]
    must_change_password: bool = False


class CreateStaffRequest(CamelModel):
    """Payload for adding a new authorized person; the admin sets the password."""

    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.manager
    branch: str | None = None
    permissions: list[str] = []


class UpdateStaffRequest(CamelModel):
    """Partial update for an existing staff account; omitted fields stay as-is."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: UserRole | None = None
    branch: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    permissions: list[str] | None = None


class PermissionItemOut(CamelModel):
    key: str
    action: str
    label: str


class PermissionGroupOut(CamelModel):
    """A module of related permissions, rendered as a checkbox group."""

    module: str
    label: str
    permissions: list[PermissionItemOut]
