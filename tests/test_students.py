"""Integration tests for student creation: code generation and pagination."""

from collections.abc import Awaitable, Callable

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


def _enrollment_payload(term_id: int) -> dict:
    return {
        "termId": term_id,
        "lang": "İngilizce",
        "level": "B1 — Orta",
        "course": "Hafta Sonu Yoğun",
        "plan": "Peşin",
        "fee": 8_000,
        "start": "2026-09-01",
    }


async def _create_term(client: AsyncClient, headers: Headers, start: str, end: str) -> int:
    response = await client.post(f"{API}/terms", headers=headers, json={"start": start, "end": end})
    return response.json()["id"]


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


async def test_create_foreign_student_with_passport(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    payload = {**_student_payload("foreign@test.com"), "passportNo": "U12345678"}
    created = await client.post(f"{API}/students", headers=headers, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["passportNo"] == "U12345678"
    assert body["isForeign"] is True
    assert body["tckn"] is None


async def test_operations_resolve_student_by_passport(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    payload = {**_student_payload("p@test.com"), "passportNo": "X99887766"}
    code = (await client.post(f"{API}/students", headers=headers, json=payload)).json()["id"]

    # Detail fetch by passport resolves the same student as the code.
    fetched = await client.get(f"{API}/students/X99887766", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == code

    # Mutations are addressable by passport too (unified resolver).
    updated = await client.patch(
        f"{API}/students/X99887766", headers=headers, json={"city": "İstanbul"}
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "İstanbul"


async def test_resolve_student_by_tckn_for_mutations(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    code = (
        await client.post(f"{API}/students", headers=headers, json=_student_payload("tk@test.com"))
    ).json()["id"]
    await client.patch(f"{API}/students/{code}", headers=headers, json={"tckn": "12345678901"})

    # Update addressed by TCKN, not the PA- code.
    updated = await client.patch(
        f"{API}/students/12345678901", headers=headers, json={"city": "Ankara"}
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Ankara"


async def test_duplicate_passport_conflicts(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    first = await client.post(
        f"{API}/students",
        headers=headers,
        json={**_student_payload("pf@test.com"), "passportNo": "DUP123"},
    )
    assert first.status_code == 201
    second = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("ps@test.com")
    )
    clash = await client.patch(
        f"{API}/students/{second.json()['id']}", headers=headers, json={"passportNo": "DUP123"}
    )
    assert clash.status_code == 409


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


async def test_add_enrollment_to_another_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("multi@test.com")
    )
    code = created.json()["id"]
    term_id = await _create_term(client, headers, "2026-09-01", "2027-01-31")

    added = await client.post(
        f"{API}/students/{code}/enrollments", headers=headers, json=_enrollment_payload(term_id)
    )
    assert added.status_code == 201
    # The new enrollment becomes the student's current view.
    assert added.json()["termId"] == term_id
    assert added.json()["course"] == "Hafta Sonu Yoğun"

    history = await client.get(f"{API}/students/{code}/enrollments", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 2


async def test_add_enrollment_rejects_duplicate_term(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students", headers=headers, json=_student_payload("dup@test.com")
    )
    code = created.json()["id"]
    term_id = await _create_term(client, headers, "2026-09-01", "2027-01-31")

    first = await client.post(
        f"{API}/students/{code}/enrollments", headers=headers, json=_enrollment_payload(term_id)
    )
    assert first.status_code == 201
    again = await client.post(
        f"{API}/students/{code}/enrollments", headers=headers, json=_enrollment_payload(term_id)
    )
    assert again.status_code == 409


async def test_approve_pending_student_activates_enrollment(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload("approve@test.com", status="pending", fee=12_000),
    )
    code = created.json()["id"]

    approved = await client.patch(f"{API}/students/{code}/approve", headers=headers)
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "active"
    # The acting user is recorded as the approver.
    assert body["approvedByName"]
    assert body["approvedAt"]


async def test_approve_without_fee_is_rejected(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    created = await client.post(
        f"{API}/students",
        headers=headers,
        json=_student_payload("nofee@test.com", status="pending", fee=0),
    )
    code = created.json()["id"]

    # A fee (and with it a payment plan) must be set before approval.
    rejected = await client.patch(f"{API}/students/{code}/approve", headers=headers)
    assert rejected.status_code == 422

    # The student stays pending after the rejected approval.
    fetched = await client.get(f"{API}/students/{code}", headers=headers)
    assert fetched.json()["status"] == "pending"


async def test_approve_unknown_student_returns_404(
    client: AsyncClient, admin: dict, login: Login
) -> None:
    headers = await login(admin["email"], admin["password"])
    response = await client.patch(f"{API}/students/PA-9999/approve", headers=headers)
    assert response.status_code == 404


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
