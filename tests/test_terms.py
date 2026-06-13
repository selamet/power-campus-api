"""Integration tests for the terms feature.

Covers term creation (naming, date validation, the ``current`` flag), listing
and ordering, partial updates, the term roster, and bulk enrollment. Bulk
enrollment is intentionally finance-free: it just registers students in a term
without assigning a fee, payment plan, installment schedule or payment record —
several tests pin that contract down, including direct database assertions.

Every endpoint is also checked for its permission gate.
"""

from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from app.apps.payments.models import Installment, Payment
from app.apps.students.models import Enrollment, Student
from app.apps.users.models import User, UserRole
from app.apps.users.permissions import Permission
from httpx import AsyncClient
from sqlalchemy import select

from .conftest import API, Headers

Login = Callable[[str, str], Awaitable[Headers]]
MakeUser = Callable[..., Awaitable[None]]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _create_term(
    client: AsyncClient,
    headers: Headers,
    *,
    start: str = "2026-09-01",
    end: str = "2027-01-31",
    name: str | None = None,
) -> dict:
    """Create a term and return its serialized body (asserts 201)."""
    body: dict = {"start": start, "end": end}
    if name is not None:
        body["name"] = name
    response = await client.post(f"{API}/terms", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _student_payload(
    email: str,
    *,
    name: str = "Roster Öğrenci",
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


async def _make_student(
    client: AsyncClient,
    headers: Headers,
    email: str,
    *,
    name: str = "Roster Öğrenci",
    level: str = "A1 — Başlangıç",
    status: str = "active",
) -> str:
    """Create a student through the API and return its public code."""
    response = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload(email, name=name, level=level, status=status),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _scoped_headers(
    make_user: MakeUser, login: Login, *, email: str, permissions: list[str]
) -> Headers:
    """A manager account holding exactly the given permissions, logged in."""
    await make_user(
        email=email, password="scoped1234", role=UserRole.manager, permissions=permissions
    )
    return await login(email, "scoped1234")


# --------------------------------------------------------------------------- #
# Term creation
# --------------------------------------------------------------------------- #


async def test_create_term_with_explicit_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(
        client, headers, name="2026 Güz", start="2026-09-01", end="2027-01-31"
    )
    assert term["name"] == "2026 Güz"
    assert term["start"] == "2026-09-01"
    assert term["end"] == "2027-01-31"
    assert isinstance(term["id"], int)


async def test_create_term_trims_name(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers, name="  2026 Güz  ")
    assert term["name"] == "2026 Güz"


async def test_create_term_autogenerates_blank_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    # A blank/whitespace name is replaced by a generated label prefixed with the
    # term's start year, so the UI always has something to show.
    term = await _create_term(client, headers, name="  ", start="2026-02-01", end="2026-06-30")
    assert term["name"].strip()
    assert term["name"].startswith("2026")


async def test_create_term_autogenerates_omitted_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    # Omitting the name entirely behaves like sending a blank one.
    term = await _create_term(client, headers, start="2027-02-01", end="2027-06-30")
    assert term["name"].startswith("2027")


async def test_create_term_allows_single_day_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    # end == start is valid; only end < start is rejected.
    term = await _create_term(client, headers, start="2026-09-01", end="2026-09-01")
    assert term["start"] == term["end"] == "2026-09-01"


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


async def test_create_term_marks_current_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    today = date.today()
    term = await _create_term(
        client,
        headers,
        start=(today - timedelta(days=30)).isoformat(),
        end=(today + timedelta(days=30)).isoformat(),
    )
    assert term["current"] is True


async def test_create_term_marks_past_term_not_current(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    today = date.today()
    term = await _create_term(
        client,
        headers,
        start=(today - timedelta(days=60)).isoformat(),
        end=(today - timedelta(days=30)).isoformat(),
    )
    assert term["current"] is False


async def test_create_term_requires_write_permission(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    headers = await _scoped_headers(
        make_user, login, email="reader@test.com", permissions=[Permission.terms_read.value]
    )
    response = await client.post(
        f"{API}/terms", headers=headers, json={"start": "2026-09-01", "end": "2027-01-31"}
    )
    assert response.status_code == 403


async def test_create_term_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/terms", json={"start": "2026-09-01", "end": "2027-01-31"}
    )
    # Missing bearer credentials are rejected before any handler runs.
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Listing terms
# --------------------------------------------------------------------------- #


async def test_list_terms_empty(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.get(f"{API}/terms", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_terms_returns_created_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    await _create_term(client, headers, start="2026-02-01", end="2026-06-30")
    listed = await client.get(f"{API}/terms", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_list_terms_orders_by_start_descending(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    await _create_term(client, headers, name="Orta", start="2025-01-01", end="2025-06-30")
    await _create_term(client, headers, name="Yeni", start="2026-09-01", end="2027-01-31")
    await _create_term(client, headers, name="Eski", start="2024-05-01", end="2024-12-31")
    listed = await client.get(f"{API}/terms", headers=headers)
    names = [term["name"] for term in listed.json()]
    assert names == ["Yeni", "Orta", "Eski"]


async def test_list_terms_requires_read_permission(
    client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    # terms:write does not imply terms:read.
    headers = await _scoped_headers(
        make_user, login, email="writer@test.com", permissions=[Permission.terms_write.value]
    )
    response = await client.get(f"{API}/terms", headers=headers)
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Updating terms
# --------------------------------------------------------------------------- #


async def test_update_term_renames(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers, start="2026-02-01", end="2026-06-30")
    updated = await client.patch(
        f"{API}/terms/{term['id']}", headers=headers, json={"name": "2026 Bahar"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "2026 Bahar"


async def test_update_term_changes_dates(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers, start="2026-02-01", end="2026-06-30")
    updated = await client.patch(
        f"{API}/terms/{term['id']}",
        headers=headers,
        json={"start": "2026-03-01", "end": "2026-07-31"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["start"] == "2026-03-01"
    assert body["end"] == "2026-07-31"
    # Name was not in the patch, so it is preserved.
    assert body["name"] == term["name"]


async def test_update_term_partial_keeps_dates(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(
        client, headers, name="İlk", start="2026-02-01", end="2026-06-30"
    )
    updated = await client.patch(
        f"{API}/terms/{term['id']}", headers=headers, json={"name": "Sonraki"}
    )
    body = updated.json()
    assert body["name"] == "Sonraki"
    assert body["start"] == "2026-02-01"
    assert body["end"] == "2026-06-30"


async def test_update_term_ignores_blank_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(
        client, headers, name="Korunan", start="2026-02-01", end="2026-06-30"
    )
    updated = await client.patch(
        f"{API}/terms/{term['id']}", headers=headers, json={"name": "   "}
    )
    assert updated.status_code == 200
    # A blank name is ignored rather than wiping the existing label.
    assert updated.json()["name"] == "Korunan"


async def test_update_term_rejects_dates_out_of_order(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers, start="2026-02-01", end="2026-06-30")
    # Moving the end before the existing start is invalid.
    updated = await client.patch(
        f"{API}/terms/{term['id']}", headers=headers, json={"end": "2026-01-01"}
    )
    assert updated.status_code == 422


async def test_update_term_missing_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.patch(
        f"{API}/terms/9999", headers=headers, json={"name": "Yok"}
    )
    assert response.status_code == 404


async def test_update_term_requires_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, admin_headers, start="2026-02-01", end="2026-06-30")
    reader = await _scoped_headers(
        make_user, login, email="reader@test.com", permissions=[Permission.terms_read.value]
    )
    response = await client.patch(
        f"{API}/terms/{term['id']}", headers=reader, json={"name": "Olmaz"}
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Term roster
# --------------------------------------------------------------------------- #


async def test_roster_empty_for_new_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers)
    roster = await client.get(f"{API}/terms/{term['id']}/students", headers=headers)
    assert roster.status_code == 200
    assert roster.json() == []


async def test_roster_missing_term_returns_empty(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    # The roster query is term-scoped; an unknown term simply has no students.
    roster = await client.get(f"{API}/terms/9999/students", headers=headers)
    assert roster.status_code == 200
    assert roster.json() == []


async def test_roster_orders_by_student_name(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    zeynep = await _make_student(client, headers, "zeynep@test.com", name="Zeynep Yıldız")
    ahmet = await _make_student(client, headers, "ahmet@test.com", name="Ahmet Demir")
    term = await _create_term(client, headers)
    await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [zeynep, ahmet]},
    )
    roster = await client.get(f"{API}/terms/{term['id']}/students", headers=headers)
    names = [row["name"] for row in roster.json()]
    assert names == ["Ahmet Demir", "Zeynep Yıldız"]


async def test_roster_only_includes_its_own_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "solo@test.com")
    term_a = await _create_term(client, headers, start="2026-09-01", end="2027-01-31")
    term_b = await _create_term(client, headers, start="2027-02-01", end="2027-06-30")
    await client.post(
        f"{API}/terms/{term_a['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    roster_b = await client.get(f"{API}/terms/{term_b['id']}/students", headers=headers)
    assert roster_b.json() == []


async def test_roster_requires_read_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, admin_headers)
    writer = await _scoped_headers(
        make_user, login, email="writer@test.com", permissions=[Permission.terms_write.value]
    )
    response = await client.get(f"{API}/terms/{term['id']}/students", headers=writer)
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Bulk enrollment
# --------------------------------------------------------------------------- #


async def test_bulk_enroll_adds_students(client: AsyncClient, admin: dict, login: Login) -> None:
    headers = await login(admin["email"], admin["password"])
    codes = [
        await _make_student(client, headers, f"r{index}@test.com") for index in range(2)
    ]
    term = await _create_term(client, headers)

    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": codes},
    )
    assert enrolled.status_code == 201
    assert len(enrolled.json()) == 2

    roster = await client.get(f"{API}/terms/{term['id']}/students", headers=headers)
    assert {row["studentId"] for row in roster.json()} == set(codes)


async def test_bulk_enroll_skips_already_enrolled(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "once@test.com")
    term = await _create_term(client, headers)

    await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    again = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    assert again.status_code == 201
    # Re-running is idempotent: no duplicate enrollment for the same student.
    assert len(again.json()) == 1


async def test_bulk_enroll_carries_student_level(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "level@test.com", level="B2 — Üst Orta")
    term = await _create_term(client, headers)
    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    # The student's current level is copied onto the new term enrollment.
    assert enrolled.json()[0]["level"] == "B2 — Üst Orta"


async def test_bulk_enroll_assigns_no_fee_or_payment(
    client: AsyncClient, admin: dict, login: Login, session_factory
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "free@test.com")
    term = await _create_term(client, headers)
    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    row = enrolled.json()[0]
    assert row["fee"] == 0
    assert row["paid"] == 0

    # The contract: simply registering a student must not create any finance.
    async with session_factory() as session:
        term_enrollments = list(
            await session.scalars(select(Enrollment).where(Enrollment.term_id == term["id"]))
        )
        installments = list(await session.scalars(select(Installment)))
        payments = list(await session.scalars(select(Payment)))
    assert len(term_enrollments) == 1
    assert term_enrollments[0].fee == 0
    assert term_enrollments[0].paid == 0
    assert installments == []
    assert payments == []


async def test_bulk_enroll_leaves_course_blank_and_defaults_metadata(
    client: AsyncClient, admin: dict, login: Login, session_factory
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "blank@test.com")
    term = await _create_term(client, headers, start="2026-09-01", end="2027-01-31")
    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    row = enrolled.json()[0]
    assert row["lang"] == ""
    assert row["course"] == ""
    assert row["status"] == "active"

    async with session_factory() as session:
        enrollment = (
            await session.scalars(select(Enrollment).where(Enrollment.term_id == term["id"]))
        ).one()
    assert enrollment.plan == ""
    # The enrollment start defaults to the term's own start date.
    assert enrollment.start_at == date(2026, 9, 1)
    # The actor who enrolled the students is recorded as the approver.
    assert enrollment.approved_by is not None
    assert enrollment.approved_at is not None


async def test_bulk_enroll_records_acting_user_as_approver(
    client: AsyncClient, admin: dict, login: Login, session_factory
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "approver@test.com")
    term = await _create_term(client, headers)
    await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    async with session_factory() as session:
        admin_user = (
            await session.scalars(select(User).where(User.email == admin["email"]))
        ).one()
        enrollment = (
            await session.scalars(select(Enrollment).where(Enrollment.term_id == term["id"]))
        ).one()
    assert enrollment.approved_by == admin_user.id


async def test_bulk_enroll_ignores_unknown_codes(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    term = await _create_term(client, headers)
    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": ["PA-DOESNOTEXIST"]},
    )
    # Unknown codes match no student, so nothing is enrolled.
    assert enrolled.status_code == 201
    assert enrolled.json() == []


async def test_bulk_enroll_mixes_new_and_existing(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    first = await _make_student(client, headers, "first@test.com", name="Bir Öğrenci")
    second = await _make_student(client, headers, "second@test.com", name="İki Öğrenci")
    term = await _create_term(client, headers)

    await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [first]},
    )
    # Second pass adds only the new student; the roster ends up with both.
    again = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [first, second]},
    )
    assert {row["studentId"] for row in again.json()} == {first, second}


async def test_bulk_enroll_empty_codes_returns_existing_roster(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "existing@test.com")
    term = await _create_term(client, headers)
    await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    empty = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": []},
    )
    assert empty.status_code == 201
    # An empty request enrolls nobody but still returns the current roster.
    assert {row["studentId"] for row in empty.json()} == {code}


async def test_bulk_enroll_skips_pending_and_inactive_students(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    active = await _make_student(client, headers, "active@test.com", status="active")
    pending = await _make_student(client, headers, "pending@test.com", status="pending")
    inactive = await _make_student(client, headers, "inactive@test.com", status="inactive")
    term = await _create_term(client, headers)

    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": [active, pending, inactive]},
    )
    assert enrolled.status_code == 201
    # Only the active student joins the term; pending/inactive are skipped.
    assert {row["studentId"] for row in enrolled.json()} == {active}


async def test_bulk_enroll_student_without_prior_enrollment_gets_blank_level(
    client: AsyncClient, admin: dict, login: Login, session_factory
) -> None:
    headers = await login(admin["email"], admin["password"])
    # A student with no existing enrollment has no level to carry over.
    async with session_factory() as session:
        session.add(
            Student(
                student_code="PA-NOENR",
                name="Kayıtsız Kişi",
                email="noenr@test.com",
                phone="0500 000 00 00",
                joined_at=date(2026, 1, 1),
            )
        )
        await session.commit()
    term = await _create_term(client, headers)
    enrolled = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=headers,
        json={"studentCodes": ["PA-NOENR"]},
    )
    assert enrolled.status_code == 201
    assert enrolled.json()[0]["level"] == ""


async def test_bulk_enroll_missing_term_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, headers, "ghost@test.com")
    response = await client.post(
        f"{API}/terms/9999/enrollments",
        headers=headers,
        json={"studentCodes": [code]},
    )
    assert response.status_code == 404


async def test_bulk_enroll_requires_students_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, admin_headers, "scoped@test.com")
    term = await _create_term(client, admin_headers)
    # Enrolling changes student registrations, so terms:write alone is not enough.
    term_writer = await _scoped_headers(
        make_user, login, email="termwriter@test.com", permissions=[Permission.terms_write.value]
    )
    response = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=term_writer,
        json={"studentCodes": [code]},
    )
    assert response.status_code == 403


async def test_bulk_enroll_allowed_with_students_write_permission(
    client: AsyncClient, admin: dict, make_user: MakeUser, login: Login
) -> None:
    admin_headers = await login(admin["email"], admin["password"])
    code = await _make_student(client, admin_headers, "allowed@test.com")
    term = await _create_term(client, admin_headers)
    enroller = await _scoped_headers(
        make_user,
        login,
        email="enroller@test.com",
        permissions=[Permission.students_write.value],
    )
    response = await client.post(
        f"{API}/terms/{term['id']}/enrollments",
        headers=enroller,
        json={"studentCodes": [code]},
    )
    assert response.status_code == 201
    assert {row["studentId"] for row in response.json()} == {code}
