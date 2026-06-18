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


async def _create_term(client: AsyncClient, headers: Headers) -> int:
    response = await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-09-01", "end": "2027-01-31"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_class(
    client: AsyncClient, headers: Headers, term_id: int, **body: object
) -> dict:
    payload = {"termId": term_id, "level": "A1 — Başlangıç", **body}
    response = await client.post(f"{API}/classes", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _make_teacher(
    client: AsyncClient, headers: Headers, *, name: str = "Hoca", status: str = "active"
) -> int:
    response = await client.post(
        f"{API}/teachers", headers=headers, json={"name": name, "status": status}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_lesson_types_catalog_endpoint(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.get(f"{API}/classes/lesson-types", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert [r["value"] for r in rows] == ["speaking", "reading", "writing", "speaking_club"]
    speaking = next(r for r in rows if r["value"] == "speaking")
    assert speaking["label"] == "Speaking"
    assert speaking["defaultSessionsPerWeek"] == 1
    assert speaking["defaultDurationMin"] == 60


async def test_class_lessons_listed_with_weekly_total(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    lessons = await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    assert lessons.status_code == 200
    body = {r["lessonType"]: r for r in lessons.json()}
    assert set(body) == {"speaking", "reading", "writing", "speaking_club"}
    # Reading default: 3/week × 60 min = 180.
    assert body["reading"]["sessionsPerWeek"] == 3
    assert body["reading"]["sessionDurationMin"] == 60
    assert body["reading"]["weeklyTotalMin"] == 180
    assert body["reading"]["lessonTypeLabel"] == "Reading"


async def test_add_lesson_allows_duplicate_type(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    added = await client.post(
        f"{API}/classes/{klass['id']}/lessons",
        headers=headers,
        json={"lessonType": "speaking", "sessionDurationMin": 45, "sessionsPerWeek": 2},
    )
    assert added.status_code == 201, added.text
    assert added.json()["weeklyTotalMin"] == 90
    listed = await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    speaking = [r for r in listed.json() if r["lessonType"] == "speaking"]
    assert len(speaking) == 2  # the seeded one plus the new duplicate


async def test_update_lesson_changes_fields_and_clears_teacher(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    teacher_id = await _make_teacher(client, headers)
    klass = await _create_class(client, headers, term_id)
    lesson_id = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()[0]["id"]
    # Assign a teacher and change sessions.
    patched = await client.patch(
        f"{API}/classes/{klass['id']}/lessons/{lesson_id}",
        headers=headers,
        json={"teacherId": teacher_id, "sessionsPerWeek": 5},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["teacherId"] == teacher_id
    assert patched.json()["sessionsPerWeek"] == 5
    # Clear the teacher.
    cleared = await client.patch(
        f"{API}/classes/{klass['id']}/lessons/{lesson_id}",
        headers=headers,
        json={"teacherId": None},
    )
    assert cleared.json()["teacherId"] is None


async def test_delete_lesson_hard_deletes(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    lessons = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()
    lesson_id = lessons[0]["id"]
    removed = await client.delete(
        f"{API}/classes/{klass['id']}/lessons/{lesson_id}", headers=headers
    )
    assert removed.status_code == 204
    remaining = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()
    assert lesson_id not in {r["id"] for r in remaining}
    assert len(remaining) == 3


async def test_lesson_rejects_zero_or_negative(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    bad = await client.post(
        f"{API}/classes/{klass['id']}/lessons",
        headers=headers,
        json={"lessonType": "writing", "sessionDurationMin": 0, "sessionsPerWeek": 1},
    )
    assert bad.status_code == 422


async def test_lesson_inactive_teacher_rejected(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    inactive = await _make_teacher(client, headers, name="Pasif", status="inactive")
    klass = await _create_class(client, headers, term_id)
    response = await client.post(
        f"{API}/classes/{klass['id']}/lessons",
        headers=headers,
        json={
            "lessonType": "writing",
            "teacherId": inactive,
            "sessionDurationMin": 60,
            "sessionsPerWeek": 1,
        },
    )
    assert response.status_code == 422


async def test_lessons_require_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, admin_headers)
    klass = await _create_class(client, admin_headers, term_id)
    await make_user(
        email="lr@test.com",
        password="scoped1234",
        role=UserRole.manager,
        permissions=[Permission.classes_read.value],
    )
    reader = await login("lr@test.com", "scoped1234")
    response = await client.post(
        f"{API}/classes/{klass['id']}/lessons",
        headers=reader,
        json={"lessonType": "speaking", "sessionDurationMin": 60, "sessionsPerWeek": 1},
    )
    assert response.status_code == 403


async def test_create_class_seeds_default_lessons(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    lessons = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()
    by_type = {r["lessonType"]: r for r in lessons}
    assert set(by_type) == {"speaking", "reading", "writing", "speaking_club"}
    assert by_type["speaking"]["sessionsPerWeek"] == 1
    assert by_type["writing"]["sessionsPerWeek"] == 3
    assert all(r["sessionDurationMin"] == 60 for r in lessons)


async def test_create_class_with_explicit_lessons(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(
        client,
        headers,
        term_id,
        lessons=[
            {"lessonType": "speaking", "sessionDurationMin": 90, "sessionsPerWeek": 2},
            {"lessonType": "reading", "sessionDurationMin": 60, "sessionsPerWeek": 3},
        ],
    )
    lessons = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()
    assert {r["lessonType"] for r in lessons} == {"speaking", "reading"}
    speaking = next(r for r in lessons if r["lessonType"] == "speaking")
    assert speaking["weeklyTotalMin"] == 180


async def test_create_class_with_inactive_lesson_teacher_rejected(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    inactive = await _make_teacher(client, headers, name="Pasif2", status="inactive")
    response = await client.post(
        f"{API}/classes",
        headers=headers,
        json={
            "termId": term_id,
            "level": "A1 — Başlangıç",
            "lessons": [
                {
                    "lessonType": "speaking",
                    "teacherId": inactive,
                    "sessionDurationMin": 60,
                    "sessionsPerWeek": 1,
                }
            ],
        },
    )
    assert response.status_code == 422
