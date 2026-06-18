from datetime import time

from app.apps.schedule.conflicts import Slot, minutes_between, overlaps, within_window


def test_overlaps_same_day_intersect():
    a = Slot(1, time(10, 0), time(10, 45))
    b = Slot(1, time(10, 30), time(11, 15))
    assert overlaps(a, b) is True


def test_no_overlap_when_adjacent():
    a = Slot(1, time(10, 0), time(10, 45))
    b = Slot(1, time(10, 45), time(11, 30))
    assert overlaps(a, b) is False


def test_no_overlap_different_weekday():
    a = Slot(1, time(10, 0), time(10, 45))
    b = Slot(2, time(10, 0), time(10, 45))
    assert overlaps(a, b) is False


def test_within_window():
    assert within_window(Slot(1, time(9), time(9, 45)), time(9), time(18)) is True
    assert within_window(Slot(1, time(8), time(8, 45)), time(9), time(18)) is False
    assert within_window(Slot(1, time(17, 30), time(18, 30)), time(9), time(18)) is False


def test_minutes_between():
    assert minutes_between(time(10, 0), time(10, 45)) == 45
