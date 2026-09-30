"""Dates in words, without strftime (its names follow the C locale, not the user's)."""
from __future__ import annotations

from datetime import date

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def fmt_date(d: date | None) -> str:
    if d is None:
        return ""
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def short_day(d: date) -> str:
    return f"{d.day}/{d.month}"
