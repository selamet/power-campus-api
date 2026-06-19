"""Pure overlap/window primitives for schedule placement and conflict checks."""

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class Slot:
    weekday: int
    start: time
    end: time


def minutes_between(a: time, b: time) -> int:
    base = date(2000, 1, 1)
    return int((datetime.combine(base, b) - datetime.combine(base, a)).total_seconds() // 60)


def overlaps(a: Slot, b: Slot) -> bool:
    if a.weekday != b.weekday:
        return False
    return a.start < b.end and b.start < a.end


def within_window(slot: Slot, day_start: time, day_end: time) -> bool:
    return slot.start >= day_start and slot.end <= day_end
