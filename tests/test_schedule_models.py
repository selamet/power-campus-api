from datetime import time

import app.models  # noqa: F401
import pytest
from app.apps.schedule.models import ScheduleConfig, ScheduleSession, TermScheduleSettings
from app.core.base import Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_schedule_tables_create_and_insert(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    day_windows_val = {"5": {"start": "10:00:00", "end": "14:00:00"}}
    async with factory() as s:
        s.add(
            TermScheduleSettings(
                term_id=1,
                working_days=[0, 1, 2, 3, 4],
                day_start=time(9),
                day_end=time(18),
                default_duration=45,
                default_per_day=6,
                break_min=10,
                teacher_rules={},
                day_windows=day_windows_val,
            )
        )
        s.add(ScheduleConfig(class_id=1, rules={"lessons": []}))
        s.add(
            ScheduleSession(
                class_lesson_id=1,
                weekday=1,
                start_time=time(10),
                end_time=time(10, 45),
            )
        )
        await s.commit()
    async with factory() as s:
        row = (await s.execute(select(TermScheduleSettings))).scalar_one()
        assert row.day_windows == day_windows_val
    async with factory() as s:
        s.add(
            ScheduleSession(
                class_lesson_id=2,
                weekday=2,
                start_time=time(11),
                end_time=time(11, 45),
                locked=True,
            )
        )
        await s.commit()
    async with factory() as s:
        rows = list((await s.execute(select(ScheduleSession).order_by(ScheduleSession.id))).scalars())
        assert rows[0].locked is False  # first record (no locked kwarg) uses default
        assert rows[1].locked is True
    await engine.dispose()
