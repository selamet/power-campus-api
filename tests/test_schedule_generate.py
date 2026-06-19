import pytest
from app.core.config import settings

API = settings.api_v1_prefix


async def _setup(client, h):
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    c = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    await client.put(
        f"{API}/classes/{c['id']}/schedule/config",
        json={"rules": {"lessons": [{"lessonType": "reading", "durationMin": 45, "sessionsPerWeek": 3}]}},
        headers=h,
    )
    return t["id"], c["id"]


@pytest.mark.asyncio
async def test_generate_class_returns_preview_without_persisting(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    _, cid = await _setup(client, h)
    gen = await client.post(f"{API}/classes/{cid}/schedule/generate", headers=h)
    assert gen.status_code == 200
    body = gen.json()
    # reading is configured for 3 sessions; the other 3 seeded lessons each get
    # one default session -> 3 + 3 = 6 placements, all feasible (empty report).
    assert len(body["sessions"]) == 6
    assert body["report"] == []
    # not persisted: the class schedule is still empty
    sched = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert sched.json() == []


@pytest.mark.asyncio
async def test_generate_without_config_uses_lesson_defaults(client, admin, login):
    """A class with seeded lessons but no builder config still generates a
    sensible schedule (one default session per lesson), so 'Üret' works
    out of the box."""
    h = await login("admin@test.com", "admin1234")
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    c = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    lessons = (await client.get(f"{API}/classes/{c['id']}/lessons", headers=h)).json()

    gen = await client.post(f"{API}/classes/{c['id']}/schedule/generate", headers=h)
    assert gen.status_code == 200
    body = gen.json()
    # one default session per seeded lesson, at the term's default duration
    assert len(body["sessions"]) == len(lessons)
    assert all(s["startTime"] and s["endTime"] for s in body["sessions"])
