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
    assert len(body["sessions"]) == 3
    assert body["report"] == []
    # not persisted: the class schedule is still empty
    sched = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert sched.json() == []
