from datetime import time

import app.models  # noqa: F401
import pytest
from app.apps.schedule.models import ScheduleConfig, ScheduleSession, TermScheduleSettings
from app.core.base import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_schedule_tables_create_and_insert(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 't.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
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
    await engine.dispose()
