import pytest

from events.exceptions import SeatPatternError
from events.seat_patterns import parse_seat_ranges, seat_exists


def test_parse_seat_ranges_accepts_valid_single_section():
    assert parse_seat_ranges("A1-3") == [("A", 1, 3)]
    assert seat_exists("A1-3", "A1") is True
    assert seat_exists("A1-3", "A2") is True
    assert seat_exists("A1-3", "A3") is True


def test_parse_seat_ranges_accepts_multiple_sections():
    assert parse_seat_ranges("A1-2,B1-3") == [("A", 1, 2), ("B", 1, 3)]
    assert seat_exists("A1-2,B1-3", "B3") is True


def test_parse_seat_ranges_rejects_malformed_pattern():
    with pytest.raises(SeatPatternError):
        parse_seat_ranges("A1,B1-3")


def test_seat_exists_returns_false_for_invalid_seat():
    assert seat_exists("A1-2,B1-3", "C1") is False
    assert seat_exists("A1-2,B1-3", "broken") is False


def test_parse_seat_ranges_rejects_reversed_range():
    with pytest.raises(SeatPatternError):
        parse_seat_ranges("A10-1")
