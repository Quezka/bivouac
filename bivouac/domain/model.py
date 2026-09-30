"""A study pack: the material for one competition (chapters, glossary, cheatsheet, cards)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum


@dataclass(frozen=True)
class Concept:
    term: str
    meaning: str
    example: str = ""


@dataclass(frozen=True)
class QuizItem:
    question: str
    answer: str


@dataclass(frozen=True)
class Section:
    title: str
    page: int | None = None  # 0-based page in the pack's source PDF


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    part: str = ""
    blurb: str = ""
    page: int | None = None
    summary: tuple[str, ...] = ()
    concept_headers: tuple[str, ...] = ()
    concepts: tuple[Concept, ...] = ()
    resources: tuple[str, ...] = ()
    quiz: tuple[QuizItem, ...] = ()
    sections: tuple[Section, ...] = ()


@dataclass(frozen=True)
class Term:
    term: str
    definition: str


@dataclass(frozen=True)
class CheatGroup:
    section: str
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class CustomCard:
    """A card the student wrote themselves."""
    id: str
    front: str
    back: str
    chapter_id: str = ""


@dataclass(frozen=True)
class Pack:
    id: str
    title: str
    subtitle: str = ""
    event: str = ""
    event_date: date | None = None
    language: str = ""
    chapters: tuple[Chapter, ...] = ()
    glossary: tuple[Term, ...] = ()
    cheatsheet: tuple[CheatGroup, ...] = ()
    cards: tuple[CustomCard, ...] = ()
    has_source: bool = False  # a PDF of the original material sits next to the pack

    def chapter(self, chapter_id: str) -> Chapter | None:
        return next((c for c in self.chapters if c.id == chapter_id), None)


class CardKind(Enum):
    CONCEPT = "concept"
    TERM = "term"
    QUESTION = "question"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Card:
    id: str
    kind: CardKind
    front: str
    back: str
    detail: str = ""
    chapter_id: str = ""  # "" for glossary and loose cards


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def cards_of(pack: Pack) -> list[Card]:
    """Every card a pack yields; ids stay stable across re-imports of the same material."""
    cards: list[Card] = []
    seen: set[str] = set()

    def add(card: Card):
        if card.id not in seen and card.front and card.back:
            seen.add(card.id)
            cards.append(card)

    for chapter in pack.chapters:
        for concept in chapter.concepts:
            add(Card(f"k:{chapter.id}:{slug(concept.term)}", CardKind.CONCEPT, concept.term,
                     concept.meaning, concept.example, chapter.id))
        for i, item in enumerate(chapter.quiz):
            add(Card(f"q:{chapter.id}:{i}", CardKind.QUESTION, item.question, item.answer,
                     "", chapter.id))
    for term in pack.glossary:
        add(Card(f"g:{slug(term.term)}", CardKind.TERM, term.term, term.definition))
    for custom in pack.cards:
        add(Card(f"u:{custom.id}", CardKind.CUSTOM, custom.front, custom.back, "",
                 custom.chapter_id))
    return cards

