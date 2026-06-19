from datetime import time

from app.apps.schedule.generator import (
    ClassRules, GenSettings, LessonReq, generate,
)

WIDE = GenSettings(working_days=[0, 1, 2, 3, 4], day_start=time(9), day_end=time(17),
                   per_day_default=6, break_min=0)

def test_consecutive_groups_same_day_adjacent():
    reqs = [LessonReq(1, 100, 7, "speaking", 45, 2, consecutive=True)]
    res = generate(reqs, WIDE, {}, {})
    ps = sorted(res.placements, key=lambda p: (p.weekday, p.start))
    assert ps[0].weekday == ps[1].weekday
    assert ps[0].end == ps[1].start  # adjacent

def test_spread_distributes_across_days_by_default():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 3)]  # not consecutive
    res = generate(reqs, WIDE, {}, {})
    days = {p.weekday for p in res.placements}
    assert len(days) == 3  # spread to distinct days

def test_separation_keeps_two_lessons_off_same_day_when_possible():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 1),
            LessonReq(2, 100, 8, "writing", 45, 1)]
    res = generate(reqs, WIDE, {100: ClassRules(separations=[["reading", "writing"]])}, {})
    by_type = {p.class_lesson_id: p.weekday for p in res.placements}
    assert by_type[1] != by_type[2]
