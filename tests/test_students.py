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


async def test_get_student_by_tckn(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("t@test.com")
    )
    code = created.json()["id"]
    await client.patch(f"{API}/students/{code}", headers=headers, json={"tckn": "12345678901"})

    fetched = await client.get(f"{API}/students/12345678901", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == code
    assert fetched.json()["tckn"] == "12345678901"


async def test_get_student_falls_back_to_code(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    """A manual student has no TCKN, so it stays reachable by its public code."""
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("c@test.com")
    )
    code = created.json()["id"]

    fetched = await client.get(f"{API}/students/{code}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == code


async def test_get_student_unknown_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    assert (await client.get(f"{API}/students/99999999999", headers=headers)).status_code == 404


async def test_assign_term_to_student(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("term@test.com")
    )
    code = created.json()["id"]
    term = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "2026 Güz", "start": "2026-09-01", "end": "2027-01-31"},
    )
    term_id = term.json()["id"]

    await client.patch(f"{API}/students/{code}", headers=headers, json={"termId": term_id})

    fetched = await client.get(f"{API}/students/{code}", headers=headers)
    assert fetched.json()["termId"] == term_id
    assert fetched.json()["termName"] == "2026 Güz"


async def test_update_to_duplicate_tckn_conflicts(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    first = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("first@test.com")
    )
    second = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("second@test.com")
    )
    await client.patch(
        f"{API}/students/{first.json()['id']}", headers=headers, json={"tckn": "11111111111"}
    )

    clash = await client.patch(
        f"{API}/students/{second.json()['id']}", headers=headers, json={"tckn": "11111111111"}
    )
    assert clash.status_code == 409
