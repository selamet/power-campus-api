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


async def _create_term(client: AsyncClient, headers: Headers) -> int:
    res = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "2026 Güz", "start": "2026-09-01", "end": "2027-01-31"},
    )
    return res.json()["id"]


async def test_approve_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload("appr@test.com", status="pending", fee=12_000),
    )
    code = created.json()["id"]
    assert (await client.patch(f"{API}/students/{code}/approve", headers=headers)).status_code == 200

    rows = (await client.get(f"{API}/students/{code}/activity", headers=headers)).json()
    kinds = [row["kind"] for row in rows]
    assert "approved" in kinds


async def test_add_enrollment_logs_activity(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = (
        await client.post(
            f"{API}/students", headers=headers, json=_student_payload("enr@test.com")
        )
    ).json()["id"]
    term_id = await _create_term(client, headers)
    added = await client.post(
        f"{API}/students/{code}/enrollments",
        headers=headers,
        json={
            "termId": term_id,
            "lang": "İngilizce",
            "level": "B1 — Orta",
            "course": "Hafta Sonu Yoğun",
            "plan": "Peşin",
            "fee": 8_000,
            "start": "2026-09-01",
        },
    )
    assert added.status_code == 201

    rows = (await client.get(f"{API}/students/{code}/activity", headers=headers)).json()
    enrolled = [row for row in rows if row["kind"] == "enrolled"]
    assert len(enrolled) == 1
    assert "B1" in enrolled[0]["message"]
