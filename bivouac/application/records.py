"""Read-only answers the use cases give the UI (never domain objects)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .types import CardKind


@dataclass(frozen=True)
class BrandingRecord:
    school: str
    place: str
    logo: str | None  # a picture file; None means the built-in school emblem


@dataclass(frozen=True)
class PackRecord:
    id: str
    title: str
    subtitle: str
    event: str
    event_date: date | None
    has_source: bool
    chapter_count: int
    card_count: int
    custom_cards: int


@dataclass(frozen=True)
class ConceptRecord:
    term: str
    meaning: str
    example: str


@dataclass(frozen=True)
class QuestionRecord:
    question: str
    answer: str


@dataclass(frozen=True)
class SectionRecord:
    title: str
    page: int | None


@dataclass(frozen=True)
class ChapterRecord:
    id: str
    title: str
    part: str
    blurb: str
    page: int | None
    summary: tuple[str, ...]
    concept_headers: tuple[str, ...]
    concepts: tuple[ConceptRecord, ...]
    resources: tuple[str, ...]
    quiz: tuple[QuestionRecord, ...]
    sections: tuple[SectionRecord, ...]
    read: bool
    cards: int
    known: int
    seen: int


@dataclass(frozen=True)
class CardRecord:
    id: str
    kind: CardKind
    front: str
    back: str
    detail: str
    chapter_id: str
    chapter_title: str
    new: bool
    interval: int  # days until it comes back; 0 for new or failed cards


@dataclass(frozen=True)
class ChoiceRecord:
    card_id: str
    prompt: str
    options: tuple[str, ...]
    answer: int
    chapter_title: str


@dataclass(frozen=True)
class ChapterProgress:
    id: str
    title: str
    known: int
    seen: int
    cards: int
    read: bool


@dataclass(frozen=True)
class OverviewRecord:
    pack: PackRecord
    today: date
    days_left: int | None  # None: no date set; negative: the event is over
    due: int
    new: int
    known: int
    seen: int
    total: int
    reviewed_today: int
    streak: int
    chapters_read: int
    history: tuple[tuple[date, int], ...]  # reviews per day, oldest first
    chapters: tuple[ChapterProgress, ...]


@dataclass(frozen=True)
class ScopeRecord:
    key: str
    label: str
    cards: int
    due: int


@dataclass(frozen=True)
class TermRecord:
    term: str
    definition: str


@dataclass(frozen=True)
class CheatRecord:
    section: str
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class DigestChapter:
    """One chapter boiled down for skimming: what to take away and the terms to know."""
    id: str
    title: str
    part: str
    page: int | None
    takeaways: tuple[str, ...]
    concepts: tuple[ConceptRecord, ...]
    read: bool


@dataclass(frozen=True)
class DigestRecord:
    chapters: tuple[DigestChapter, ...]
    total_chapters: int  # before searching
    total_concepts: int
