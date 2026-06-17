"""Teacher API schemas."""

from pydantic import EmailStr, Field

from app.apps.teachers.models import Teacher, TeacherStatus
from app.core.schemas import CamelModel


class TeacherOut(CamelModel):
    """A teacher as returned to the frontend."""

    id: int
    name: str
    email: EmailStr | None
    phone: str | None
    status: TeacherStatus
    languages: list[str]
    levels: list[str]
    note: str | None
    class_count: int

    @classmethod
    def from_model(cls, teacher: Teacher, *, class_count: int) -> "TeacherOut":
        return cls(
            id=teacher.id,
            name=teacher.name,
            email=teacher.email,
            phone=teacher.phone,
            status=teacher.status,
            languages=teacher.languages or [],
            levels=teacher.levels or [],
            note=teacher.note,
            class_count=class_count,
        )


class TeacherCreate(CamelModel):
    """Payload for creating a teacher."""

    name: str
    email: EmailStr | None = None
    phone: str | None = None
    status: TeacherStatus = TeacherStatus.active
    languages: list[str] = Field(default_factory=lambda: ["İngilizce"])
    levels: list[str] = Field(default_factory=list)
    note: str | None = None


class TeacherUpdate(CamelModel):
    """Partial update of a teacher."""

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: TeacherStatus | None = None
    languages: list[str] | None = None
    levels: list[str] | None = None
    note: str | None = None
