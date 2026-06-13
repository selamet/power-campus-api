"""Authentication request/response schemas."""

from pydantic import EmailStr

from app.apps.users.models import UserRole
from app.core.schemas import CamelModel


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class StaffOut(CamelModel):
    """Authenticated user as consumed by the frontend (`Staff`)."""

    name: str
    role: UserRole
    email: EmailStr
    branch: str | None = None
    permissions: list[str] = []


class LoginResponse(CamelModel):
    user: StaffOut
    token: str
