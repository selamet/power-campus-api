"""Integration tests for the lesson module (catalog, CRUD, create-time seeding)."""

from collections.abc import Awaitable, Callable

from app.apps.classes.lessons import (
    LessonType,
)
from app.apps.users.models import UserRole
from app.apps.users.permissions import Permission
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


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
    assert "defaultSessionsPerWeek" not in speaking
    assert "defaultDurationMin" not in speaking


async def test_class_lessons_listed(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    lessons = await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    assert lessons.status_code == 200
    body = {r["lessonType"]: r for r in lessons.json()}
    assert set(body) == {"speaking", "reading", "writing", "speaking_club"}
    assert body["reading"]["lessonTypeLabel"] == "Reading"
    assert "sessionsPerWeek" not in body["reading"]
    assert "sessionDurationMin" not in body["reading"]
    assert "weeklyTotalMin" not in body["reading"]


async def test_add_lesson_allows_duplicate_type(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    klass = await _create_class(client, headers, term_id)
    added = await client.post(
        f"{API}/classes/{klass['id']}/lessons",
        headers=headers,
        json={"lessonType": "speaking"},
    )
    assert added.status_code == 201, added.text
    listed = await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    speaking = [r for r in listed.json() if r["lessonType"] == "speaking"]
    assert len(speaking) == 2  # the seeded one plus the new duplicate


async def test_update_lesson_changes_teacher(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    teacher_id = await _make_teacher(client, headers)
    klass = await _create_class(client, headers, term_id)
    lesson_id = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()[0]["id"]
    # Assign a teacher.
    patched = await client.patch(
        f"{API}/classes/{klass['id']}/lessons/{lesson_id}",
        headers=headers,
        json={"teacherId": teacher_id},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["teacherId"] == teacher_id
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
        json={"lessonType": "speaking"},
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
    assert {l["lessonType"] for l in lessons} == {"speaking", "reading", "writing", "speaking_club"}
    assert all("sessionDurationMin" not in l and "sessionsPerWeek" not in l for l in lessons)


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
            {"lessonType": "speaking"},
            {"lessonType": "reading"},
        ],
    )
    lessons = (
        await client.get(f"{API}/classes/{klass['id']}/lessons", headers=headers)
    ).json()
    assert {r["lessonType"] for r in lessons} == {"speaking", "reading"}


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
                }
            ],
        },
    )
    assert response.status_code == 422
