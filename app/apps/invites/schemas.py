"""Invite and welcome-form schemas."""

from datetime import date

from pydantic import EmailStr, field_validator

from app.apps.invites.models import InviteStatus
from app.core.schemas import CamelModel


def _validate_tckn(value: str) -> str:
    cleaned = value.strip()
    if not (cleaned.isdigit() and len(cleaned) == 11):
        raise ValueError("TCKN 11 haneli rakamlardan oluşmalı.")
    return cleaned


class CreateInviteRequest(CamelModel):
    tckn: str
    phone: str
    name: str | None = None
    lang: str
    course: str

    _check_tckn = field_validator("tckn")(_validate_tckn)


class InviteOut(CamelModel):
    """Invite returned to staff after creation, with the shareable link path."""

    tckn: str
    name: str | None
    lang: str
    course: str
    status: InviteStatus
    path: str


class InvitePublicOut(CamelModel):
    """Minimal invite data the public welcome form uses to pre-fill itself."""

    tckn: str
    name: str | None
    lang: str
    course: str
    status: InviteStatus


class WelcomeSubmitRequest(CamelModel):
    """Details a student submits through their personal welcome link."""

    name: str
    email: EmailStr
    phone: str
    birth_date: date | None = None
    gender: str | None = None
    city: str | None = None
    address: str | None = None
    education_level: str | None = None
    school: str | None = None
    department: str | None = None
    grade: str | None = None
    contact_name: str | None = None
    contact_relation: str | None = None
    contact_phone: str | None = None


class WelcomeSubmitResponse(CamelModel):
    student_code: str
    status: str  # resulting student status, e.g. "pending"
