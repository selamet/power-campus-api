import pytest
from app.core.config import settings

API = settings.api_v1_prefix


async def _setup(client, h):
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    c = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    await client.put(
        f"{API}/classes/{c['id']}/schedule/config",
        json={"rules": {"lessons": [{"lessonType": "reading", "durationMin": 45, "sessionsPerWeek": 2}]}},
        headers=h,
    )
    return t["id"], c["id"]


@pytest.mark.asyncio
async def test_apply_persists_and_replaces(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    _, cid = await _setup(client, h)

    first = await client.post(f"{API}/classes/{cid}/schedule/apply", headers=h)
    assert first.status_code == 200
    assert first.json()["applied"] == 2
    sched = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert len(sched.json()) == 2

    # Applying again replaces, not appends.
    second = await client.post(f"{API}/classes/{cid}/schedule/apply", headers=h)
    assert second.json()["applied"] == 2
    sched2 = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert len(sched2.json()) == 2
