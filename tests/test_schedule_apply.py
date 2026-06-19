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

    # reading is configured for 2 sessions; the other 3 seeded lessons each get
    # one default session -> 2 + 3 = 5 placed and persisted.
    first = await client.post(f"{API}/classes/{cid}/schedule/apply", headers=h)
    assert first.status_code == 200
    assert first.json()["applied"] == 5
    sched = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert len(sched.json()) == 5

    # Applying again replaces, not appends.
    second = await client.post(f"{API}/classes/{cid}/schedule/apply", headers=h)
    assert second.json()["applied"] == 5
    sched2 = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert len(sched2.json()) == 5


@pytest.mark.asyncio
async def test_apply_preserves_locked_session(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    _, class_id = await _setup(client, h)

    # First apply to create sessions
    first = await client.post(f"{API}/classes/{class_id}/schedule/apply", headers=h)
    assert first.status_code == 200

    # Get the applied sessions and lock the first one
    listed = await client.get(f"{API}/classes/{class_id}/schedule", headers=h)
    sessions = listed.json()
    assert sessions, "apply en az bir oturum üretmeli"
    locked_id = sessions[0]["id"]
    locked_weekday = sessions[0]["weekday"]
    locked_start = sessions[0]["startTime"]
    await client.patch(
        f"{API}/schedule/sessions/{locked_id}/lock",
        json={"locked": True},
        headers=h,
    )

    # Re-apply
    await client.post(f"{API}/classes/{class_id}/schedule/apply", headers=h)

    # Locked session must be preserved with same id/slot
    again = await client.get(f"{API}/classes/{class_id}/schedule", headers=h)
    kept = [s for s in again.json() if s["id"] == locked_id]
    assert len(kept) == 1
    assert kept[0]["locked"] is True
    assert kept[0]["weekday"] == locked_weekday
    assert kept[0]["startTime"] == locked_start
