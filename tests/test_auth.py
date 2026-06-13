"""Integration tests for authentication, permission gating and password reset."""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


async def test_login_returns_all_permissions_for_admin(client: AsyncClient, admin: dict) -> None:
    response = await client.post(f"{API}/auth/login", json=admin)
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["role"] == "admin"
    assert len(user["permissions"]) == 8  # admin implicitly holds every permission


async def test_login_rejects_wrong_password(client: AsyncClient, admin: dict) -> None:
    response = await client.post(
        f"{API}/auth/login", json={"email": admin["email"], "password": "wrong"}
    )
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.get(f"{API}/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == admin["email"]


async def test_protected_endpoint_requires_auth(client: AsyncClient) -> None:
    assert (await client.get(f"{API}/students")).status_code in (401, 403)


async def test_permission_gating_blocks_missing_scope(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    await make_user(
        email="reader@test.com",
        password="reader12",
        role=UserRole.manager,
        permissions=["students:read"],
    )
    headers = await login("reader@test.com", "reader12")

    assert (await client.get(f"{API}/students", headers=headers)).status_code == 200
    # No finance:read -> blocked before the route body runs.
    blocked = await client.get(f"{API}/students/PA-1/installments", headers=headers)
    assert blocked.status_code == 403


async def test_forced_reset_blocks_api_until_changed(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    await make_user(
        email="new@test.com",
        password="temp1234",
        role=UserRole.manager,
        permissions=["students:read", "finance:read"],
        must_change=True,
    )
    headers = await login("new@test.com", "temp1234")

    # Protected resources are blocked while a reset is owed...
    assert (await client.get(f"{API}/students", headers=headers)).status_code == 403
    # ...but /me and /password stay reachable so the user can recover.
    assert (await client.get(f"{API}/auth/me", headers=headers)).status_code == 200

    changed = await client.post(
        f"{API}/auth/password",
        headers=headers,
        json={"currentPassword": "temp1234", "newPassword": "brandnew1"},
    )
    assert changed.status_code == 200
    assert changed.json()["mustChangePassword"] is False

    # Same token now passes the gate.
    assert (await client.get(f"{API}/students", headers=headers)).status_code == 200


async def test_change_password_rejects_wrong_current(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    await make_user(
        email="u@test.com", password="temp1234", role=UserRole.manager, must_change=True
    )
    headers = await login("u@test.com", "temp1234")
    response = await client.post(
        f"{API}/auth/password",
        headers=headers,
        json={"currentPassword": "wrong-one", "newPassword": "brandnew1"},
    )
    assert response.status_code == 400
