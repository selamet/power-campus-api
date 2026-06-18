from datetime import time

from app.apps.schedule.generator import (
    ClassRules, GenSettings, LessonReq, TeacherRule, generate,
)

SETTINGS = GenSettings(working_days=[0, 1, 2, 3, 4], day_start=time(9), day_end=time(12),
                       per_day_default=3, break_min=0)


def test_places_all_when_room():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 3)]
    res = generate(reqs, SETTINGS, {}, {})
    assert len(res.placements) == 3
    assert not res.unplaced
    # all within window 09:00-12:00
    assert all(time(9) <= p.start and p.end <= time(12) for p in res.placements)


def test_never_double_books_teacher_across_classes():
    # Same teacher 7, two classes, lots of sessions in a tight window.
    reqs = [LessonReq(1, 100, 7, "reading", 45, 3), LessonReq(2, 200, 7, "reading", 45, 3)]
    res = generate(reqs, SETTINGS, {}, {})
    placed = [p for p in res.placements if p.teacher_id == 7]
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            same = a.weekday == b.weekday and a.start < b.end and b.start < a.end
            assert not same


def test_respects_class_closed_weekday():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 2)]
    res = generate(reqs, SETTINGS, {100: ClassRules(closed_weekdays=[0, 1, 2, 3])}, {})
    assert all(p.weekday == 4 for p in res.placements)


def test_per_day_cap_limits_same_day():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 3)]
    res = generate(reqs, SETTINGS, {100: ClassRules(per_day_cap=1)}, {})
    days = [p.weekday for p in res.placements]
    assert len(days) == len(set(days))  # at most one per day


def test_reports_unplaced_when_infeasible():
    tight = GenSettings(working_days=[0], day_start=time(9), day_end=time(9, 45),
                        per_day_default=3, break_min=0)
    reqs = [LessonReq(1, 100, 7, "reading", 45, 3)]
    res = generate(reqs, tight, {}, {})
    assert len(res.placements) == 1
    assert len(res.unplaced) == 2


def test_teacher_unavailable_weekday():
    reqs = [LessonReq(1, 100, 7, "reading", 45, 1)]
    res = generate(reqs, SETTINGS, {}, {7: TeacherRule(unavailable_weekdays=[0, 1, 2, 3])})
    assert res.placements[0].weekday == 4
