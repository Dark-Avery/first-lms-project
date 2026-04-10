from __future__ import annotations

import re

from events.exceptions import SeatPatternError

_RANGE_PATTERN = re.compile(r"^(?P<section>[A-Z])(?P<start>\d+)-(?P<end>\d+)$")
_SEAT_PATTERN = re.compile(r"^(?P<section>[A-Z])(?P<number>\d+)$")


def parse_seat_ranges(seats_pattern: str) -> list[tuple[str, int, int]]:
    if not seats_pattern:
        raise SeatPatternError("Seat pattern must not be empty.")

    ranges: list[tuple[str, int, int]] = []
    for chunk in seats_pattern.split(","):
        match = _RANGE_PATTERN.fullmatch(chunk)
        if match is None:
            raise SeatPatternError("Seat pattern has invalid format.")

        start = int(match.group("start"))
        end = int(match.group("end"))
        if start > end:
            raise SeatPatternError("Seat pattern range start must not exceed range end.")

        ranges.append((match.group("section"), start, end))

    return ranges


def seat_exists(seats_pattern: str, seat: str) -> bool:
    seat_match = _SEAT_PATTERN.fullmatch(seat)
    if seat_match is None:
        return False

    section = seat_match.group("section")
    number = int(seat_match.group("number"))

    for range_section, start, end in parse_seat_ranges(seats_pattern):
        if range_section == section and start <= number <= end:
            return True

    return False
