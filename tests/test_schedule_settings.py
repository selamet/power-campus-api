import pytest
from app.core.config import settings

API = settings.api_v1_prefix

async def _term(client, headers):
    r = await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=headers)
    return r.json()["id"]

@pytest.mark.asyncio
async def test_settings_default_then_update(client, admin, login):
    h = await login("admin@test.com", "admin1234")
    term_id = await _term(client, h)

    got = await client.get(f"{API}/terms/{term_id}/schedule/settings", headers=h)
    assert got.status_code == 200
    body = got.json()
    assert body["defaultDuration"] == 45
    assert body["defaultPerDay"] == 3
    assert body["workingDays"] == [0, 1, 2, 3, 4]

    assert body["dayWindows"] == {}

    upd = await client.put(
        f"{API}/terms/{term_id}/schedule/settings",
        json={"workingDays": [0, 1, 2, 3, 4, 5], "dayStart": "08:00", "dayEnd": "20:00",
              "defaultDuration": 50, "defaultPerDay": 4, "breakMin": 10,
              "teacherRules": {"12": {"unavailableWeekdays": [4]}},
              "dayWindows": {"5": {"start": "10:00", "end": "14:00"}}},
        headers=h,
    )
    assert upd.status_code == 200
    assert upd.json()["defaultDuration"] == 50
    assert upd.json()["teacherRules"]["12"]["unavailableWeekdays"] == [4]
    assert upd.json()["dayWindows"]["5"]["start"] == "10:00:00"
