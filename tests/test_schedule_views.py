from datetime import time

import pytest
from app.core.config import settings

API = settings.api_v1_prefix


async def _class_with_sessions(client, login, session_factory):
    h = await login("admin@test.com", "admin1234")
    t = (await client.post(f"{API}/terms", json={"name": "T", "start": "2026-01-01", "end": "2026-06-01"}, headers=h)).json()
    c = (await client.post(f"{API}/classes", json={"termId": t["id"], "level": "A1"}, headers=h)).json()
    lessons = (await client.get(f"{API}/classes/{c['id']}/lessons", headers=h)).json()
    cl_id = lessons[0]["id"]
    from app.apps.schedule.models import ScheduleSession
    async with session_factory() as s:
        s.add(ScheduleSession(class_lesson_id=cl_id, weekday=1, start_time=time(10), end_time=time(10, 45)))
        s.add(ScheduleSession(class_lesson_id=cl_id, weekday=2, start_time=time(10), end_time=time(10, 45)))
        await s.commit()
    return h, t["id"], c["id"]


@pytest.mark.asyncio
async def test_class_and_term_views(client, admin, login, session_factory):
    h, tid, cid = await _class_with_sessions(client, login, session_factory)

    cls_view = await client.get(f"{API}/classes/{cid}/schedule", headers=h)
    assert cls_view.status_code == 200
    assert len(cls_view.json()) == 2
    assert all("startTime" in s and "weekday" in s for s in cls_view.json())

    term_view = await client.get(f"{API}/terms/{tid}/schedule", headers=h)
    assert len(term_view.json()) == 2

    one_day = cls_view.json()[0]["weekday"]
    filtered = await client.get(f"{API}/terms/{tid}/schedule?weekday={one_day}", headers=h)
    assert all(s["weekday"] == one_day for s in filtered.json())
