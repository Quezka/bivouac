"""Spaced repetition (a small SM-2) and multiple-choice drills."""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum

from .model import Card, CardKind


class Grade(Enum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


MIN_EASE = 1.3
KNOWN_DAYS = 7  # a card seen again after a week or more counts as known


@dataclass(frozen=True)
class ReviewState:
    card_id: str
    due: date
    interval: int = 0  # days
    ease: float = 2.5
    reps: int = 0  # successful reviews in a row
    lapses: int = 0

    @property
    def known(self) -> bool:
        return self.interval >= KNOWN_DAYS


def review(state: ReviewState | None, card_id: str, grade: Grade, today: date,
           deadline: date | None = None) -> ReviewState:
    """The state after answering a card. A deadline (the competition) caps the gap so
    every card still comes round once more before the day."""
    s = state or ReviewState(card_id, today)
    if grade is Grade.AGAIN:
        return replace(s, due=today, interval=0, reps=0, lapses=s.lapses + 1,
                       ease=max(MIN_EASE, s.ease - 0.2))
    if grade is Grade.HARD:
        interval, ease = max(1, round(s.interval * 1.2)), max(MIN_EASE, s.ease - 0.15)
    elif grade is Grade.GOOD:
        interval, ease = (1 if s.reps == 0 else 3 if s.reps == 1
                          else round(s.interval * s.ease)), s.ease
    else:
        interval, ease = (4 if s.reps == 0 else round(max(s.interval, 1) * s.ease * 1.3),
                          s.ease + 0.15)
    if deadline is not None and deadline > today:
        interval = min(interval, max(1, (deadline - today).days // 2))
    interval = max(1, interval)
    return replace(s, due=today + timedelta(days=interval), interval=interval, ease=ease,
                   reps=s.reps + 1)


@dataclass(frozen=True)
class ChoiceQuestion:
    card_id: str
    prompt: str
    options: tuple[str, ...]
    answer: int
    chapter_id: str


CHOICE_KINDS = (CardKind.CONCEPT, CardKind.TERM, CardKind.CUSTOM)


def choice_question(target: Card, pool: list[Card], rng: random.Random,
                    size: int = 4) -> ChoiceQuestion:
    """"Which term fits this definition?", with wrong answers from the same chapter first."""
    others = [c for c in pool if c.kind in CHOICE_KINDS and c.front.lower() != target.front.lower()]
    near = [c for c in others if target.chapter_id and c.chapter_id == target.chapter_id]
    far = [c for c in others if c not in near]
    rng.shuffle(near)
    rng.shuffle(far)
    options: list[str] = []
    for c in near + far:
        if c.front not in options:
            options.append(c.front)
        if len(options) == size - 1:
            break
    answer = rng.randrange(len(options) + 1)
    options.insert(answer, target.front)
    return ChoiceQuestion(target.id, target.back, tuple(options), answer, target.chapter_id)
