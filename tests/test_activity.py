"""Integration tests for the per-student activity log."""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]


def _student_payload(email: str, *, status: str = "active", fee: int = 10_000) -> dict:
    return {
        "name": "Test Öğrenci",
        "lang": "İngilizce",
        "level": "A1 — Başlangıç",
        "course": "Online Canlı",
        "status": status,
        "phone": "0500 000 00 00",
        "start": "2026-02-01",
        "fee": fee,
        "plan": "Peşin",
        "joined": "2026-01-01",
        "email": email,
    }


async def test_create_student_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("act1@test.com")
    )
    code = created.json()["id"]

    res = await client.get(f"{API}/students/{code}/activity", headers=headers)
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "created"
    assert rows[0]["actorName"] == "Test User"
    assert rows[0]["message"]


async def test_activity_requires_read_permission(
    client: AsyncClient, make_user: Callable[..., Awaitable[None]], login: Login
) -> None:
    await make_user(email="noperm@test.com", password="pw12345678", role=UserRole.manager)
    headers = await login("noperm@test.com", "pw12345678")
    res = await client.get(f"{API}/students/PA-9999/activity", headers=headers)
    assert res.status_code == 403
