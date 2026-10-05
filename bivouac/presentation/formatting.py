"""Dates in words, without strftime (its names follow the C locale, not the user's)."""
from __future__ import annotations

from datetime import date

from . import i18n


def fmt_date(d: date | None) -> str:
    if d is None:
        return ""
    return f"{i18n.weekday_short(d)} {d.day} {i18n.month_of(d)} {d.year}"


def short_day(d: date) -> str:
    return f"{d.day}/{d.month}"
