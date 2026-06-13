"""Integration tests for student creation: code generation and pagination."""

from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]


def _student_payload(email: str) -> dict:
    return {
        "name": "Test Öğrenci",
        "lang": "İngilizce",
        "level": "A1 — Başlangıç",
        "course": "Online Canlı",
        "phone": "0500 000 00 00",
        "start": "2026-02-01",
        "fee": 10_000,
        "plan": "Peşin",
        "joined": "2026-01-01",
        "email": email,
    }


async def test_create_student_generates_sequential_codes(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    first = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("a@test.com")
    )
    second = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("b@test.com")
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == "PA-1060"
    assert second.json()["id"] == "PA-1061"


async def test_students_pagination(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    for index in range(3):
        created = await client.post(
            f"{API}/students", headers=headers, json=_student_payload(f"s{index}@test.com")
        )
        assert created.status_code == 201

    assert len((await client.get(f"{API}/students", headers=headers)).json()) == 3
    assert len((await client.get(f"{API}/students?limit=2", headers=headers)).json()) == 2
    assert len((await client.get(f"{API}/students?limit=2&offset=2", headers=headers)).json()) == 1


async def test_students_list_rejects_invalid_limit(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    assert (await client.get(f"{API}/students?limit=0", headers=headers)).status_code == 422
    assert (await client.get(f"{API}/students?limit=999", headers=headers)).status_code == 422
