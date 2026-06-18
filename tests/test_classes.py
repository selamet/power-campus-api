"""Integration tests for the classes feature.

Covers class CRUD (auto section numbering, uniqueness), the roster, manual and
automatic student assignment, and unassignment — plus every endpoint's
permission gate. Class membership lives on the term enrollment, so a student
must already be in the class's term and be active to be assigned.
"""

from collections.abc import Awaitable, Callable

from app.apps.users.models import UserRole
from app.apps.users.permissions import Permission
from httpx import AsyncClient

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _create_term(
    client: AsyncClient, headers: Headers, *, start: str = "2026-09-01", end: str = "2027-01-31"
) -> int:
    response = await client.post(
        f"{API}/terms", headers=headers, json={"start": start, "end": end}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _student_payload(
    email: str,
    *,
    name: str = "Sınıf Öğrenci",
    level: str = "A1 — Başlangıç",
    status: str = "active",
) -> dict:
    return {
        "name": name,
        "lang": "İngilizce",
        "level": level,
        "course": "Online Canlı",
        "status": status,
        "phone": "0500 000 00 00",
        "start": "2026-02-01",
        "fee": 10_000,
        "plan": "Peşin",
        "joined": "2026-01-01",
        "email": email,
    }


async def _student_in_term(
    client: AsyncClient,
    headers: Headers,
    email: str,
    term_id: int,
    *,
    name: str = "Sınıf Öğrenci",
    level: str = "A1 — Başlangıç",
    status: str = "active",
) -> str:
    """Create a student and place their enrollment in the given term."""
    created = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload(email, name=name, level=level, status=status),
    )
    assert created.status_code == 201, created.text
    code = created.json()["id"]
    patched = await client.patch(
        f"{API}/students/{code}", headers=headers, json={"termId": term_id}
    )
    assert patched.status_code == 200, patched.text
    return code


async def _student_in_term_ex(
    client: AsyncClient,
    headers: Headers,
    email: str,
    term_id: int,
    *,
    level: str = "A1 — Başlangıç",
    start: str = "2026-02-01",
    paid: int = 0,
    fee: int = 10_000,
) -> str:
    """Like ``_student_in_term`` but with a distinct start date and finance, so
    ordering and payment-filter behavior can be exercised."""
    payload = _student_payload(email, level=level)
    payload.update({"start": start, "paid": paid, "fee": fee})
    created = await client.post(f"{API}/students", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    code = created.json()["id"]
    patched = await client.patch(
        f"{API}/students/{code}", headers=headers, json={"termId": term_id}
    )
    assert patched.status_code == 200, patched.text
    return code


async def _create_class(
    client: AsyncClient,
    headers: Headers,
    term_id: int,
    *,
    level: str = "A1 — Başlangıç",
    section: int | None = None,
) -> dict:
    body: dict = {"termId": term_id, "level": level}
    if section is not None:
        body["section"] = section
    response = await client.post(f"{API}/classes", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def _scoped_headers(
    make_user: MakeUser, login: Login, *, email: str, permissions: list[str]
) -> Headers:
    await make_user(
        email=email, password="scoped1234", role=UserRole.manager, permissions=permissions
    )
    return await login(email, "scoped1234")


# --------------------------------------------------------------------------- #
# Class creation
# --------------------------------------------------------------------------- #


async def test_create_class_auto_numbers_sections(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    first = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    second = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    assert first["section"] == 1
    assert first["name"] == "A1/1"
    assert second["section"] == 2
    assert second["name"] == "A1/2"


async def test_create_class_explicit_section(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    created = await _create_class(client, headers, term_id, level="B2 — Orta-Üstü", section=5)
    assert created["section"] == 5
    assert created["name"] == "B2/5"


async def test_create_class_rejects_duplicate(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=1)
    clash = await client.post(
        f"{API}/classes",
        headers=headers,
        json={"termId": term_id, "level": "A1 — Başlangıç", "section": 1},
    )
    assert clash.status_code == 409


async def test_create_class_unknown_term_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.post(
        f"{API}/classes", headers=headers, json={"termId": 9999, "level": "A1 — Başlangıç"}
    )
    assert response.status_code == 404


async def test_create_class_requires_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, admin_headers)
    reader = await _scoped_headers(
        make_user, login, email="cr@test.com", permissions=[Permission.classes_read.value]
    )
    response = await client.post(
        f"{API}/classes", headers=reader, json={"termId": term_id, "level": "A1 — Başlangıç"}
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Listing / update / delete
# --------------------------------------------------------------------------- #


async def test_list_classes_filters_by_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_a = await _create_term(client, headers, start="2026-09-01", end="2027-01-31")
    term_b = await _create_term(client, headers, start="2027-02-01", end="2027-06-30")
    await _create_class(client, headers, term_a, level="A1 — Başlangıç")
    await _create_class(client, headers, term_b, level="B1 — Orta")

    only_a = await client.get(f"{API}/classes?term_id={term_a}", headers=headers)
    assert only_a.status_code == 200
    assert [c["termId"] for c in only_a.json()] == [term_a]

    all_classes = await client.get(f"{API}/classes", headers=headers)
    assert len(all_classes.json()) == 2


async def test_list_classes_requires_read_permission(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    writer = await _scoped_headers(
        make_user, login, email="cw@test.com", permissions=[Permission.classes_write.value]
    )
    response = await client.get(f"{API}/classes", headers=writer)
    assert response.status_code == 403


async def test_update_class_changes_section(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    created = await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=1)
    updated = await client.patch(
        f"{API}/classes/{created['id']}", headers=headers, json={"section": 3}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "A1/3"


async def test_update_class_missing_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.patch(f"{API}/classes/9999", headers=headers, json={"section": 2})
    assert response.status_code == 404


async def test_delete_class_keeps_students_in_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    code = await _student_in_term(client, headers, "keep@test.com", term_id)
    school_class = await _create_class(client, headers, term_id)
    await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=headers,
        json={"studentCodes": [code]},
    )

    deleted = await client.delete(f"{API}/classes/{school_class['id']}", headers=headers)
    assert deleted.status_code == 204

    # The student stays enrolled in the term, just unassigned from a class.
    roster = await client.get(f"{API}/terms/{term_id}/students", headers=headers)
    assert {row["studentId"] for row in roster.json()} == {code}


# --------------------------------------------------------------------------- #
# Manual assignment
# --------------------------------------------------------------------------- #


async def test_assign_students_to_class(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    codes = [
        await _student_in_term(client, headers, f"a{i}@test.com", term_id, name=f"Öğrenci {i}")
        for i in range(2)
    ]
    school_class = await _create_class(client, headers, term_id)
    assigned = await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=headers,
        json={"studentCodes": codes},
    )
    assert assigned.status_code == 201
    assert {row["studentId"] for row in assigned.json()} == set(codes)

    listed = await client.get(f"{API}/classes", headers=headers)
    assert listed.json()[0]["studentCount"] == 2


async def test_assign_skips_students_not_in_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    in_term = await _student_in_term(client, headers, "in@test.com", term_id)
    # Created but never placed in the term.
    outsider = (
        await client.post(f"{API}/students", headers=headers, json=_student_payload("out@test.com"))
    ).json()["id"]
    school_class = await _create_class(client, headers, term_id)

    assigned = await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=headers,
        json={"studentCodes": [in_term, outsider]},
    )
    assert {row["studentId"] for row in assigned.json()} == {in_term}


async def test_assign_skips_pending_and_inactive(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    active = await _student_in_term(client, headers, "ac@test.com", term_id, status="active")
    pending = await _student_in_term(client, headers, "pe@test.com", term_id, status="pending")
    inactive = await _student_in_term(client, headers, "ia@test.com", term_id, status="inactive")
    school_class = await _create_class(client, headers, term_id)

    assigned = await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=headers,
        json={"studentCodes": [active, pending, inactive]},
    )
    assert {row["studentId"] for row in assigned.json()} == {active}


async def test_assign_moves_student_between_classes(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    code = await _student_in_term(client, headers, "move@test.com", term_id)
    class_one = await _create_class(client, headers, term_id, section=1)
    class_two = await _create_class(client, headers, term_id, section=2)

    await client.post(
        f"{API}/classes/{class_one['id']}/students", headers=headers, json={"studentCodes": [code]}
    )
    # Assigning to the second class moves the student out of the first.
    await client.post(
        f"{API}/classes/{class_two['id']}/students", headers=headers, json={"studentCodes": [code]}
    )
    first_roster = await client.get(f"{API}/classes/{class_one['id']}/students", headers=headers)
    second_roster = await client.get(f"{API}/classes/{class_two['id']}/students", headers=headers)
    assert first_roster.json() == []
    assert {row["studentId"] for row in second_roster.json()} == {code}


async def test_assign_requires_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, admin_headers)
    code = await _student_in_term(client, admin_headers, "perm@test.com", term_id)
    school_class = await _create_class(client, admin_headers, term_id)
    reader = await _scoped_headers(
        make_user, login, email="ro@test.com", permissions=[Permission.classes_read.value]
    )
    response = await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=reader,
        json={"studentCodes": [code]},
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Automatic assignment
# --------------------------------------------------------------------------- #


async def test_auto_assign_matches_level_only(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    a1 = await _student_in_term(client, headers, "lvl1@test.com", term_id, level="A1 — Başlangıç")
    a1_other = await _student_in_term(
        client, headers, "lvl2@test.com", term_id, level="A1 — Başlangıç"
    )
    b1 = await _student_in_term(client, headers, "lvl3@test.com", term_id, level="B1 — Orta")
    school_class = await _create_class(client, headers, term_id, level="A1 — Başlangıç")

    assigned = await client.post(f"{API}/classes/{school_class['id']}/auto-assign", headers=headers)
    assert assigned.status_code == 200
    # Only the matching-level students are pulled in; the B1 student is not.
    assert {row["studentId"] for row in assigned.json()} == {a1, a1_other}
    assert b1 not in {row["studentId"] for row in assigned.json()}


async def test_auto_assign_skips_already_assigned(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    code = await _student_in_term(client, headers, "asg@test.com", term_id, level="A1 — Başlangıç")
    class_one = await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=1)
    class_two = await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=2)

    await client.post(
        f"{API}/classes/{class_one['id']}/students", headers=headers, json={"studentCodes": [code]}
    )
    # Already assigned to class one, so auto-assign on class two skips them.
    auto = await client.post(f"{API}/classes/{class_two['id']}/auto-assign", headers=headers)
    assert auto.json() == []


# --------------------------------------------------------------------------- #
# Unassignment
# --------------------------------------------------------------------------- #


async def test_unassign_keeps_student_in_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    code = await _student_in_term(client, headers, "un@test.com", term_id)
    school_class = await _create_class(client, headers, term_id)
    await client.post(
        f"{API}/classes/{school_class['id']}/students",
        headers=headers,
        json={"studentCodes": [code]},
    )

    removed = await client.delete(
        f"{API}/classes/{school_class['id']}/students/{code}", headers=headers
    )
    assert removed.status_code == 204

    class_roster = await client.get(f"{API}/classes/{school_class['id']}/students", headers=headers)
    term_roster = await client.get(f"{API}/terms/{term_id}/students", headers=headers)
    assert class_roster.json() == []
    assert {row["studentId"] for row in term_roster.json()} == {code}


# --------------------------------------------------------------------------- #
# Configurable auto-assignment (builder)
# --------------------------------------------------------------------------- #


async def test_auto_assign_limit_caps_count(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    for i in range(3):
        await _student_in_term_ex(client, headers, f"cap{i}@test.com", term_id)
    school_class = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    assigned = await client.post(
        f"{API}/classes/{school_class['id']}/auto-assign",
        headers=headers,
        json={"limit": 2},
    )
    assert assigned.status_code == 200
    assert len(assigned.json()) == 2


async def test_auto_assign_order_oldest_then_newest(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    old = await _student_in_term_ex(client, headers, "old@test.com", term_id, start="2026-01-01")
    new = await _student_in_term_ex(client, headers, "new@test.com", term_id, start="2026-03-01")
    klass = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    oldest = await client.post(
        f"{API}/classes/{klass['id']}/auto-assign",
        headers=headers,
        json={"limit": 1, "order": "oldest"},
    )
    assert {r["studentId"] for r in oldest.json()} == {old}
    # Reset, then newest-first picks the other student.
    await client.delete(f"{API}/classes/{klass['id']}/students/{old}", headers=headers)
    newest = await client.post(
        f"{API}/classes/{klass['id']}/auto-assign",
        headers=headers,
        json={"limit": 1, "order": "newest"},
    )
    assert {r["studentId"] for r in newest.json()} == {new}


async def test_auto_assign_paid_only_filters_unpaid(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    paid = await _student_in_term_ex(
        client, headers, "paid@test.com", term_id, paid=10_000, fee=10_000
    )
    await _student_in_term_ex(client, headers, "owe@test.com", term_id, paid=0, fee=10_000)
    klass = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    assigned = await client.post(
        f"{API}/classes/{klass['id']}/auto-assign",
        headers=headers,
        json={"payment": "paidOnly"},
    )
    assert {r["studentId"] for r in assigned.json()} == {paid}


async def test_auto_assign_include_assigned_moves_students(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    code = await _student_in_term_ex(client, headers, "mv@test.com", term_id)
    one = await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=1)
    two = await _create_class(client, headers, term_id, level="A1 — Başlangıç", section=2)
    await client.post(
        f"{API}/classes/{one['id']}/students", headers=headers, json={"studentCodes": [code]}
    )
    # Default (includeAssigned false) skips the already-assigned student.
    skip = await client.post(f"{API}/classes/{two['id']}/auto-assign", headers=headers, json={})
    assert skip.json() == []
    # includeAssigned true moves them into class two.
    moved = await client.post(
        f"{API}/classes/{two['id']}/auto-assign",
        headers=headers,
        json={"includeAssigned": True},
    )
    assert {r["studentId"] for r in moved.json()} == {code}


async def test_auto_assign_empty_body_keeps_old_behavior(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    a = await _student_in_term_ex(client, headers, "e1@test.com", term_id)
    b = await _student_in_term_ex(client, headers, "e2@test.com", term_id)
    klass = await _create_class(client, headers, term_id, level="A1 — Başlangıç")
    assigned = await client.post(f"{API}/classes/{klass['id']}/auto-assign", headers=headers)
    assert {r["studentId"] for r in assigned.json()} == {a, b}


async def test_create_class_with_auto_assign(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    for i in range(3):
        await _student_in_term_ex(client, headers, f"ca{i}@test.com", term_id)
    created = await client.post(
        f"{API}/classes",
        headers=headers,
        json={
            "termId": term_id,
            "level": "A1 — Başlangıç",
            "autoAssign": {"limit": 2, "order": "oldest"},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["studentCount"] == 2
    roster = await client.get(
        f"{API}/classes/{created.json()['id']}/students", headers=headers
    )
    assert len(roster.json()) == 2


async def test_create_class_without_auto_assign_is_empty(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term_id = await _create_term(client, headers)
    await _student_in_term_ex(client, headers, "noaa@test.com", term_id)
    created = await client.post(
        f"{API}/classes", headers=headers, json={"termId": term_id, "level": "A1 — Başlangıç"}
    )
    assert created.status_code == 201
    assert created.json()["studentCount"] == 0
