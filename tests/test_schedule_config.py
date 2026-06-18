import pytest
from app.core.config import settings

API = settings.api_v1_prefix


async def _class(client, h):
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    c = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    return c["id"]


@pytest.mark.asyncio
async def test_config_default_then_save(client, login, admin):
    h = await login(admin["email"], admin["password"])
    cid = await _class(client, h)

    got = await client.get(f"{API}/classes/{cid}/schedule/config", headers=h)
    assert got.status_code == 200
    assert got.json()["rules"] == {}

    rules = {"lessons": [{"lessonType": "speaking", "durationMin": 45, "sessionsPerWeek": 2}],
             "perDayCap": 3, "closedWeekdays": [0]}
    put = await client.put(f"{API}/classes/{cid}/schedule/config", json={"rules": rules}, headers=h)
    assert put.status_code == 200
    assert put.json()["rules"]["perDayCap"] == 3
