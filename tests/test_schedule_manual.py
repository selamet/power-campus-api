import pytest
from app.core.config import settings

API = settings.api_v1_prefix


async def _two_lessons_same_teacher(client, h):
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    teacher = (await client.post(f"{API}/teachers", json={"name": "Hoca", "status": "active"}, headers=h)).json()
    c1 = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    c2 = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A2"}, headers=h)).json()
    l1 = (await client.get(f"{API}/classes/{c1['id']}/lessons", headers=h)).json()[0]
    l2 = (await client.get(f"{API}/classes/{c2['id']}/lessons", headers=h)).json()[0]
    # assign same teacher to both lessons
    await client.patch(f"{API}/classes/{c1['id']}/lessons/{l1['id']}", json={"teacherId": teacher["id"]}, headers=h)
    await client.patch(f"{API}/classes/{c2['id']}/lessons/{l2['id']}", json={"teacherId": teacher["id"]}, headers=h)
    return l1["id"], l2["id"]


@pytest.mark.asyncio
async def test_add_then_conflicting_add_returns_409(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    l1, l2 = await _two_lessons_same_teacher(client, h)

    ok = await client.post(f"{API}/schedule/sessions",
                           json={"classLessonId": l1, "weekday": 1, "startTime": "10:00", "endTime": "10:45"},
                           headers=h)
    assert ok.status_code == 201

    clash = await client.post(f"{API}/schedule/sessions",
                              json={"classLessonId": l2, "weekday": 1, "startTime": "10:30", "endTime": "11:15"},
                              headers=h)
    assert clash.status_code == 409


@pytest.mark.asyncio
async def test_delete_session(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    l1, _ = await _two_lessons_same_teacher(client, h)
    created = await client.post(f"{API}/schedule/sessions",
                                json={"classLessonId": l1, "weekday": 2, "startTime": "09:00", "endTime": "09:45"},
                                headers=h)
    sid = created.json()["id"]
    deleted = await client.delete(f"{API}/schedule/sessions/{sid}", headers=h)
    assert deleted.status_code == 204
