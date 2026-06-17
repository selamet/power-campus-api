"""Integration tests for admin staff management."""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


async def test_admin_creates_staff_requiring_reset(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/users",
        headers=headers,
        json={
            "name": "Yeni Kişi",
            "email": "yeni@test.com",
            "password": "gecici12",
            "role": "manager",
            "permissions": ["students:read"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mustChangePassword"] is True
    assert body["permissions"] == ["students:read"]
    assert body["isActive"] is True


async def test_duplicate_email_is_rejected(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    payload = {
        "name": "Dup",
        "email": "dup@test.com",
        "password": "gecici12",
        "role": "manager",
        "permissions": [],
    }
    assert (await client.post(f"{API}/users", headers=headers, json=payload)).status_code == 201
    assert (await client.post(f"{API}/users", headers=headers, json=payload)).status_code == 422


async def test_invalid_permission_is_rejected(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/users",
        headers=headers,
        json={
            "name": "Bad",
            "email": "bad@test.com",
            "password": "gecici12",
            "role": "manager",
            "permissions": ["bogus:perm"],
        },
    )
    assert response.status_code == 422


async def test_admin_cannot_deactivate_self(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    listing = await client.get(f"{API}/users", headers=headers)
    admin_id = listing.json()[0]["id"]
    response = await client.patch(
        f"{API}/users/{admin_id}", headers=headers, json={"isActive": False}
    )
    assert response.status_code == 422


async def test_non_admin_cannot_manage_staff(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    await make_user(
        email="manager@test.com",
        password="pass1234",
        role=UserRole.manager,
        permissions=["students:read"],
    )
    headers = await login("manager@test.com", "pass1234")
    assert (await client.get(f"{API}/users", headers=headers)).status_code == 403


async def test_permission_catalog_lists_modules(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.get(f"{API}/users/permissions/catalog", headers=headers)
    assert response.status_code == 200
    modules = [group["module"] for group in response.json()]
    assert modules == [
        "dashboard",
        "students",
        "finance",
        "invites",
        "terms",
        "classes",
        "teachers",
        "users",
    ]
