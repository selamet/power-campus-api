"""Integration tests for term creation, listing, naming and updates."""

from collections.abc import Awaitable, Callable

from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]


async def test_create_term_with_explicit_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "2026 Güz", "start": "2026-09-01", "end": "2027-01-31"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "2026 Güz"


async def test_create_term_autogenerates_blank_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "  ", "start": "2026-02-01", "end": "2026-06-30"},
    )
    assert response.status_code == 201
    # A playful name is filled in and stored, so the UI always has a label.
    assert response.json()["name"].strip()


async def test_list_terms(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-02-01", "end": "2026-06-30"}
    )
    listed = await client.get(f"{API}/terms", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_update_term_renames(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-02-01", "end": "2026-06-30"}
    )
    term_id = created.json()["id"]
    updated = await client.patch(
        f"{API}/terms/{term_id}", headers=headers, json={"name": "2026 Bahar"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "2026 Bahar"


async def test_create_term_rejects_end_before_start(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/terms",
        headers=headers,
        json={"name": "Ters", "start": "2026-06-30", "end": "2026-02-01"},
    )
    assert response.status_code == 422


def _student_payload(email: str) -> dict:
    return {
        "name": "Roster Öğrenci",
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


def _bulk_payload(codes: list[str]) -> dict:
    return {"studentCodes": codes}


async def test_bulk_enroll_adds_students(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    codes = []
    for index in range(2):
        created = await client.post(
            f"{API}/students", headers=headers, json=_student_payload(f"r{index}@test.com")
        )
        codes.append(created.json()["id"])
    term = await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-09-01", "end": "2027-01-31"}
    )
    term_id = term.json()["id"]

    enrolled = await client.post(
        f"{API}/terms/{term_id}/enrollments", headers=headers, json=_bulk_payload(codes)
    )
    assert enrolled.status_code == 201
    assert len(enrolled.json()) == 2

    roster = await client.get(f"{API}/terms/{term_id}/students", headers=headers)
    assert {row["studentId"] for row in roster.json()} == set(codes)


async def test_bulk_enroll_skips_already_enrolled(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("once@test.com")
    )
    code = created.json()["id"]
    term = await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-09-01", "end": "2027-01-31"}
    )
    term_id = term.json()["id"]

    await client.post(
        f"{API}/terms/{term_id}/enrollments", headers=headers, json=_bulk_payload([code])
    )
    again = await client.post(
        f"{API}/terms/{term_id}/enrollments", headers=headers, json=_bulk_payload([code])
    )
    assert again.status_code == 201
    # No duplicate enrollment was created for the same student in the same term.
    assert len(again.json()) == 1
