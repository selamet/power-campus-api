"""Authentication request/response schemas."""

from pydantic import EmailStr, Field

from app.apps.users.models import UserRole
from app.core.schemas import CamelModel


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(CamelModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class StaffOut(CamelModel):
    """Authenticated user as consumed by the frontend (`Staff`)."""

    name: str
    role: UserRole
    email: EmailStr
    branch: str | None = None
    permissions: list[str] = []
    must_change_password: bool = False


class LoginResponse(CamelModel):
    user: StaffOut
    token: str
