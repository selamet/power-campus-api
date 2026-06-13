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
