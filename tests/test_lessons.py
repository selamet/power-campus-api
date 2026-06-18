"""Integration tests for the lesson module (catalog, CRUD, create-time seeding)."""

from collections.abc import Awaitable, Callable

from app.apps.classes.lessons import (
    DEFAULT_SESSION_DURATION_MIN,
    LessonType,
    default_lessons,
)
from app.apps.users.models import UserRole
from app.apps.users.permissions import Permission
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


def test_default_lessons_catalog() -> None:
    rows = default_lessons()
    assert [lt for lt, _, _ in rows] == [
        LessonType.speaking,
        LessonType.reading,
        LessonType.writing,
        LessonType.speaking_club,
    ]
    by_type = {lt: (spw, dur) for lt, spw, dur in rows}
    assert by_type[LessonType.speaking] == (1, DEFAULT_SESSION_DURATION_MIN)
    assert by_type[LessonType.reading] == (3, DEFAULT_SESSION_DURATION_MIN)
    assert by_type[LessonType.writing] == (3, DEFAULT_SESSION_DURATION_MIN)
    assert by_type[LessonType.speaking_club] == (3, DEFAULT_SESSION_DURATION_MIN)
    assert DEFAULT_SESSION_DURATION_MIN == 60
