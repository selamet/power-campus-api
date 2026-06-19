"""Greedy + bounded-backtracking weekly schedule generator.

Structural rules (A) are never violated; a request that cannot be placed is
reported as Unplaced. Limiting rules (B) shrink the candidate slots. Placement
preferences (C) are layered in by candidate ordering (see _candidate_slots).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.apps.schedule.conflicts import Slot, minutes_between, overlaps, within_window


@dataclass
class LessonReq:
    class_lesson_id: int
    class_id: int
    teacher_id: int | None
    lesson_type: str
    duration_min: int
    count: int
    pinned_weekday: int | None = None
    consecutive: bool = False


@dataclass
class GenSettings:
    working_days: list[int]
    day_start: time
    day_end: time
    per_day_default: int
    break_min: int
    day_windows: dict[int, tuple[time, time]] = field(default_factory=dict)


@dataclass
class ClassRules:
    per_day_cap: int | None = None
    closed_weekdays: list[int] = field(default_factory=list)
    daily_pattern: list[list[str]] = field(default_factory=list)
    separations: list[list[str]] = field(default_factory=list)


@dataclass
class TeacherRule:
    unavailable_weekdays: list[int] = field(default_factory=list)
    max_per_day: int | None = None
    max_per_week: int | None = None


@dataclass
class Placement:
    class_lesson_id: int
    class_id: int
    teacher_id: int | None
    weekday: int
    start: time
    end: time


@dataclass
class Unplaced:
    class_lesson_id: int
    class_id: int
    lesson_type: str
    reason: str


@dataclass
class GenResult:
    placements: list[Placement]
    unplaced: list[Unplaced]


_BASE = date(2000, 1, 1)


def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(_BASE, t) + timedelta(minutes=minutes)).time()


def _window_for(settings: GenSettings, weekday: int) -> tuple[time, time]:
    return settings.day_windows.get(weekday, (settings.day_start, settings.day_end))


def _day_starts(day_start: time, day_end: time, break_min: int, duration: int) -> list[time]:
    """All candidate start times within [day_start, day_end), stepping by duration+break."""
    step = duration + break_min
    starts: list[time] = []
    cur = day_start
    while minutes_between(cur, day_end) >= duration:
        starts.append(cur)
        cur = _add_minutes(cur, step)
    return starts


def _explode(reqs: list[LessonReq]) -> list[LessonReq]:
    """One LessonReq per individual session (count=1), preserving attributes."""
    out: list[LessonReq] = []
    for r in reqs:
        for _ in range(r.count):
            out.append(
                LessonReq(r.class_lesson_id, r.class_id, r.teacher_id, r.lesson_type,
                          r.duration_min, 1, r.pinned_weekday, r.consecutive)
            )
    return out


def _order(units: list[LessonReq], teacher_rules: dict[int, TeacherRule]) -> list[LessonReq]:
    """Most-constrained first: pinned weekday, then teacher-availability-limited."""
    def key(u: LessonReq) -> tuple[int, int, int]:
        pinned = 0 if u.pinned_weekday is not None else 1
        limited = 0 if (u.teacher_id in teacher_rules) else 1
        return (pinned, limited, u.class_lesson_id)
    return sorted(units, key=key)


def _candidate_slots(
    unit: LessonReq, settings: GenSettings,
    crules: ClassRules, trule: TeacherRule | None,
) -> list[Slot]:
    """Feasible slots for a unit under limiting rules B1/B2/B3/B4-day."""
    days = [d for d in settings.working_days if d not in crules.closed_weekdays]
    if unit.pinned_weekday is not None:
        days = [d for d in days if d == unit.pinned_weekday]
    if trule is not None:
        days = [d for d in days if d not in trule.unavailable_weekdays]
    slots: list[Slot] = []
    for d in days:
        ds, de = _window_for(settings, d)
        for st in _day_starts(ds, de, settings.break_min, unit.duration_min):
            end = _add_minutes(st, unit.duration_min)
            slot = Slot(d, st, end)
            if within_window(slot, ds, de):
                slots.append(slot)
    return slots


def _count_on_day(items: list[Placement], weekday: int, *, class_id: int | None = None,
                  teacher_id: int | None = None) -> int:
    n = 0
    for p in items:
        if p.weekday != weekday:
            continue
        if class_id is not None and p.class_id != class_id:
            continue
        if teacher_id is not None and p.teacher_id != teacher_id:
            continue
        n += 1
    return n


def _count_week(items: list[Placement], teacher_id: int) -> int:
    return sum(1 for p in items if p.teacher_id == teacher_id)


def _structurally_ok(
    unit: LessonReq, slot: Slot, placed: list[Placement],
    settings: GenSettings, crules: ClassRules, trule: TeacherRule | None,
) -> bool:
    cap = crules.per_day_cap if crules.per_day_cap is not None else settings.per_day_default
    if _count_on_day(placed, slot.weekday, class_id=unit.class_id) >= cap:
        return False
    if trule is not None and unit.teacher_id is not None:
        if trule.max_per_day is not None and \
           _count_on_day(placed, slot.weekday, teacher_id=unit.teacher_id) >= trule.max_per_day:
            return False
        if trule.max_per_week is not None and \
           _count_week(placed, unit.teacher_id) >= trule.max_per_week:
            return False
    for p in placed:
        ps = Slot(p.weekday, p.start, p.end)
        if not overlaps(Slot(slot.weekday, slot.start, slot.end), ps):
            continue
        if p.class_id == unit.class_id:  # A2 class double-book
            return False
        if unit.teacher_id is not None and p.teacher_id == unit.teacher_id:  # A1 teacher
            return False
    return True


def _same_type_today(placed: list[Placement], class_id: int, weekday: int,
                     class_lesson_id: int) -> list[Placement]:
    return [p for p in placed if p.class_id == class_id and p.weekday == weekday
            and p.class_lesson_id == class_lesson_id]


def _types_on_day(placed: list[Placement], class_id: int, weekday: int,
                  lesson_type_by_cl: dict[int, str]) -> set[str]:
    return {lesson_type_by_cl[p.class_lesson_id] for p in placed
            if p.class_id == class_id and p.weekday == weekday
            and p.class_lesson_id in lesson_type_by_cl}


def _score_slot(unit: LessonReq, slot: Slot, placed: list[Placement],
                crules: ClassRules, lesson_type_by_cl: dict[int, str]) -> int:
    score = 0
    same = _same_type_today(placed, unit.class_id, slot.weekday, unit.class_lesson_id)
    if unit.consecutive:
        # Reward same-day adjacency to an existing same-type session (C4).
        if any(p.end == slot.start or slot.end == p.start for p in same):
            score += 100
        elif same:
            score += 20
    else:
        # Spread: penalize stacking the same lesson on a day already used (C6).
        score -= 30 * len(same)
    # Separation (C7): penalize sharing a day with a separated lesson type.
    present = _types_on_day(placed, unit.class_id, slot.weekday, lesson_type_by_cl)
    for group in crules.separations:
        others = {g for g in group if g != unit.lesson_type}
        if unit.lesson_type in group and present.intersection(others):
            score -= 60
    # Earlier in the week/day is a mild tiebreaker for determinism.
    score -= slot.weekday + minutes_between(time(0), slot.start) // 600
    return score


def generate(
    reqs: list[LessonReq], settings: GenSettings,
    class_rules: dict[int, ClassRules], teacher_rules: dict[int, TeacherRule],
) -> GenResult:
    units = _order(_explode(reqs), teacher_rules)
    placed: list[Placement] = []
    unplaced: list[Unplaced] = []
    lesson_type_by_cl = {u.class_lesson_id: u.lesson_type for u in units}

    def backtrack(i: int) -> bool:
        if i == len(units):
            return True
        unit = units[i]
        crules = class_rules.get(unit.class_id, ClassRules())
        trule = teacher_rules.get(unit.teacher_id) if unit.teacher_id is not None else None
        candidates = _candidate_slots(unit, settings, crules, trule)
        candidates.sort(
            key=lambda s: (-_score_slot(unit, s, placed, crules, lesson_type_by_cl),
                           s.weekday, s.start),
        )
        for slot in candidates:
            if _structurally_ok(unit, slot, placed, settings, crules, trule):
                placed.append(Placement(unit.class_lesson_id, unit.class_id, unit.teacher_id,
                                        slot.weekday, slot.start, slot.end))
                if backtrack(i + 1):
                    return True
                placed.pop()
        # Could not place this unit anywhere: skip it (partial result) and continue.
        unplaced.append(Unplaced(unit.class_lesson_id, unit.class_id, unit.lesson_type,
                                 "Uygun boş slot bulunamadı"))
        return backtrack(i + 1)

    backtrack(0)
    return GenResult(placements=placed, unplaced=unplaced)
