"""Integration tests for the teachers feature: CRUD, status filter, permissions."""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from app.apps.users.permissions import Permission
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]

def _teacher_payload(name: str = "Ayşe Öğretmen", **extra) -> dict:
    return {"name": name, "email": "t@test.com", "phone": "0500 000 00 00",
            "levels": ["A1 — Başlangıç", "B1 — Orta"], **extra}

async def _scoped_headers(make_user, login, *, email, permissions) -> Headers:
    await make_user(email=email, password="scoped1234", role=UserRole.manager, permissions=permissions)
    return await login(email, "scoped1234")

async def test_create_and_get_teacher(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload())
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Ayşe Öğretmen"
    assert body["status"] == "active"
    assert body["languages"] == ["İngilizce"]
    assert body["levels"] == ["A1 — Başlangıç", "B1 — Orta"]
    assert body["classCount"] == 0

    fetched = await client.get(f"{API}/teachers/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

async def test_list_and_status_filter(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    a = await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload("A", email="a@t.com"))
    b = await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload("B", email="b@t.com"))
    await client.patch(f"{API}/teachers/{b.json()['id']}", headers=headers, json={"status": "inactive"})

    all_rows = await client.get(f"{API}/teachers", headers=headers)
    assert len(all_rows.json()) == 2
    active = await client.get(f"{API}/teachers?status=active", headers=headers)
    assert [t["id"] for t in active.json()] == [a.json()["id"]]
    inactive = await client.get(f"{API}/teachers?status=inactive", headers=headers)
    assert [t["id"] for t in inactive.json()] == [b.json()["id"]]

async def test_update_teacher(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    tid = (await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload())).json()["id"]
    updated = await client.patch(f"{API}/teachers/{tid}", headers=headers,
                                 json={"phone": "0532 111 22 33", "levels": ["C1 — İleri"]})
    assert updated.status_code == 200
    assert updated.json()["phone"] == "0532 111 22 33"
    assert updated.json()["levels"] == ["C1 — İleri"]

async def test_get_unknown_teacher_404(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    assert (await client.get(f"{API}/teachers/9999", headers=headers)).status_code == 404

async def test_create_requires_write_permission(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    headers = await _scoped_headers(make_user, login, email="ro@t.com",
                                    permissions=[Permission.teachers_read.value])
    res = await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload())
    assert res.status_code == 403

async def test_list_requires_read_permission(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    headers = await _scoped_headers(make_user, login, email="wo@t.com",
                                    permissions=[Permission.teachers_write.value])
    res = await client.get(f"{API}/teachers", headers=headers)
    assert res.status_code == 403


async def _create_term(client, headers, start="2026-09-01", end="2027-01-31") -> int:
    res = await client.post(f"{API}/terms", headers=headers, json={"start": start, "end": end})
    return res.json()["id"]


async def _create_class(client, headers, term_id, level="A1 — Başlangıç") -> int:
    res = await client.post(f"{API}/classes", headers=headers, json={"termId": term_id, "level": level})
    return res.json()["id"]


async def test_assign_teacher_to_class(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    tid = (await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload())).json()["id"]
    term_id = await _create_term(client, headers)
    cid = await _create_class(client, headers, term_id)

    assigned = await client.patch(f"{API}/classes/{cid}", headers=headers, json={"teacherId": tid})
    assert assigned.status_code == 200
    assert assigned.json()["teacherId"] == tid
    assert assigned.json()["teacherName"] == "Ayşe Öğretmen"

    cleared = await client.patch(f"{API}/classes/{cid}", headers=headers, json={"teacherId": None})
    assert cleared.json()["teacherId"] is None
    assert cleared.json()["teacherName"] is None


async def test_assign_inactive_teacher_rejected(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    tid = (await client.post(f"{API}/teachers", headers=headers, json=_teacher_payload())).json()["id"]
    await client.patch(f"{API}/teachers/{tid}", headers=headers, json={"status": "inactive"})
    term_id = await _create_term(client, headers)
    cid = await _create_class(client, headers, term_id)

    res = await client.patch(f"{API}/classes/{cid}", headers=headers, json={"teacherId": tid})
    assert res.status_code == 422


async def test_assign_missing_teacher_404(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    cid = await _create_class(client, headers, term_id)
    res = await client.patch(f"{API}/classes/{cid}", headers=headers, json={"teacherId": 9999})
    assert res.status_code == 404
