"""What the UI sends to the use cases."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PackInput:
    title: str
    event: str = ""
    event_date: date | None = None
    subtitle: str = ""


@dataclass(frozen=True)
class CardInput:
    front: str
    back: str
    chapter_id: str = ""


@dataclass(frozen=True)
class BrandingInput:
    school: str
    place: str
    logo: str | None = None
