"""Use cases for studying a pack: overview, chapters, flashcards, drills, reference."""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..domain.model import Card, Chapter, Pack, cards_of
from ..domain.srs import CHOICE_KINDS, Grade, ReviewState, choice_question, review
from .errors import NotFound
from .library import pack_record
from .ports import Clock, KeyValueStore, PackStore, ProgressStore
from .records import (
    ChapterProgress, ChapterRecord, CardRecord, CheatRecord, ChoiceRecord, ConceptRecord,
    DigestChapter, DigestRecord, OverviewRecord, QuestionRecord, ScopeRecord, SectionRecord,
    TermRecord,
)
from .types import SCOPE_ALL, SCOPE_CHAPTER, SCOPE_GLOSSARY

NEW_PER_DAY = 20
HISTORY_DAYS = 14


def _matches(query: str, *texts: str) -> bool:
    words = query.lower().split()
    haystack = " ".join(texts).lower()
    return all(w in haystack for w in words)


class StudyService:
    def __init__(self, packs: PackStore, progress: ProgressStore, clock: Clock,
                 settings: KeyValueStore, rng: random.Random | None = None):
        self._packs = packs
        self._progress = progress
        self._clock = clock
        self._settings = settings
        self._rng = rng or random.Random()

    # ---- helpers ----------------------------------------------------------------
    def _load(self, pack_id: str) -> Pack:
        return self._packs.load(pack_id)

    def _in_scope(self, pack: Pack, scope: str) -> list[Card]:
        cards = cards_of(pack)
        if scope == SCOPE_GLOSSARY:
            return [c for c in cards if c.id.startswith("g:")]
        if scope.startswith(SCOPE_CHAPTER):
            chapter_id = scope.removeprefix(SCOPE_CHAPTER)
            if pack.chapter(chapter_id) is None:
                raise NotFound(f"There's no chapter {chapter_id}.")
            return [c for c in cards if c.chapter_id == chapter_id]
        return cards

    def _card_record(self, pack: Pack, card: Card, state: ReviewState | None) -> CardRecord:
        chapter = pack.chapter(card.chapter_id) if card.chapter_id else None
        return CardRecord(card.id, card.kind, card.front, card.back, card.detail,
                          card.chapter_id, chapter.title if chapter else "", state is None,
                          state.interval if state else 0)

    def _chapter_record(self, chapter: Chapter, cards: list[Card],
                        states: dict[str, ReviewState], read: set[str]) -> ChapterRecord:
        mine = [c for c in cards if c.chapter_id == chapter.id]
        return ChapterRecord(
            chapter.id, chapter.title, chapter.part, chapter.blurb, chapter.page,
            chapter.summary, chapter.concept_headers,
            tuple(ConceptRecord(c.term, c.meaning, c.example) for c in chapter.concepts),
            chapter.resources,
            tuple(QuestionRecord(q.question, q.answer) for q in chapter.quiz),
            tuple(SectionRecord(s.title, s.page) for s in chapter.sections),
            chapter.id in read, len(mine),
            sum(1 for c in mine if c.id in states and states[c.id].known),
            sum(1 for c in mine if c.id in states))

    def _new_today(self, pack_id: str, states: dict[str, ReviewState]) -> int:
        return self._progress.first_seen_on(pack_id, self._clock.today())

    # ---- overview -----------------------------------------------------------------
    def overview(self, pack_id: str) -> OverviewRecord:
        pack = self._load(pack_id)
        today = self._clock.today()
        cards = cards_of(pack)
        states = self._progress.states(pack_id)
        read = self._progress.read_chapters(pack_id)
        mine = {c.id: states[c.id] for c in cards if c.id in states}
        due = sum(1 for s in mine.values() if s.due <= today)
        unseen = len(cards) - len(mine)
        new_left = max(0, min(unseen, self.new_per_day() - self._new_today(pack_id, states)))
        log = self._progress.reviews_by_day(pack_id, today - timedelta(days=400))
        streak, day = 0, today if log.get(today) else today - timedelta(days=1)
        while log.get(day):
            streak, day = streak + 1, day - timedelta(days=1)
        history = tuple((today - timedelta(days=i), log.get(today - timedelta(days=i), 0))
                        for i in reversed(range(HISTORY_DAYS)))
        chapters = tuple(
            ChapterProgress(r.id, r.title, r.known, r.seen, r.cards, r.read)
            for r in (self._chapter_record(c, cards, states, read) for c in pack.chapters))
        return OverviewRecord(
            pack_record(pack), today,
            (pack.event_date - today).days if pack.event_date else None,
            due, new_left, sum(1 for s in mine.values() if s.known), len(mine), len(cards),
            log.get(today, 0), streak, sum(1 for c in pack.chapters if c.id in read), history,
            chapters)

    def new_per_day(self) -> int:
        try:
            return max(0, int(self._settings.get("new_per_day") or NEW_PER_DAY))
        except ValueError:
            return NEW_PER_DAY

    def set_new_per_day(self, count: int) -> None:
        self._settings.set("new_per_day", str(max(0, min(count, 500))))

    # ---- chapters -----------------------------------------------------------------
    def chapters(self, pack_id: str) -> list[ChapterRecord]:
        pack = self._load(pack_id)
        cards, states = cards_of(pack), self._progress.states(pack_id)
        read = self._progress.read_chapters(pack_id)
        return [self._chapter_record(c, cards, states, read) for c in pack.chapters]

    def chapter(self, pack_id: str, chapter_id: str) -> ChapterRecord:
        found = next((c for c in self.chapters(pack_id) if c.id == chapter_id), None)
        if found is None:
            raise NotFound(f"There's no chapter {chapter_id}.")
        return found

    def digest(self, pack_id: str, query: str = "") -> DigestRecord:
        """Every chapter's takeaways and key terms in one skimmable list.

        A search keeps a whole chapter when its title matches, otherwise only the
        takeaways and terms that do (and drops chapters left with nothing)."""
        pack = self._load(pack_id)
        read = self._progress.read_chapters(pack_id)
        found = []
        for c in pack.chapters:
            takeaways, concepts = c.summary, c.concepts
            if query.strip() and not _matches(query, c.id, c.title, c.part):
                takeaways = tuple(t for t in takeaways if _matches(query, t))
                concepts = tuple(k for k in concepts if _matches(query, k.term, k.meaning,
                                                                 k.example))
            if takeaways or concepts:
                found.append(DigestChapter(
                    c.id, c.title, c.part, c.page, takeaways,
                    tuple(ConceptRecord(k.term, k.meaning, k.example) for k in concepts),
                    c.id in read))
        return DigestRecord(tuple(found), sum(1 for c in pack.chapters if c.summary or c.concepts),
                            sum(len(c.concepts) for c in pack.chapters))

    def set_read(self, pack_id: str, chapter_id: str, read: bool) -> None:
        if self._load(pack_id).chapter(chapter_id) is None:
            raise NotFound(f"There's no chapter {chapter_id}.")
        self._progress.set_read(pack_id, chapter_id, read)

    # ---- flashcards ---------------------------------------------------------------
    def scopes(self, pack_id: str) -> list[ScopeRecord]:
        pack = self._load(pack_id)
        states, today = self._progress.states(pack_id), self._clock.today()

        def scope(key, label):
            cards = self._in_scope(pack, key)
            due = sum(1 for c in cards if c.id in states and states[c.id].due <= today)
            return ScopeRecord(key, label, len(cards), due)

        found = [scope(SCOPE_ALL, "Everything")]
        if pack.glossary:
            found.append(scope(SCOPE_GLOSSARY, "Glossary"))
        found += [scope(SCOPE_CHAPTER + c.id, f"{c.id} · {c.title}") for c in pack.chapters]
        return [s for s in found if s.cards]

    def queue(self, pack_id: str, scope: str = SCOPE_ALL, cram: bool = False) -> list[CardRecord]:
        """Cards to go through now: those due, oldest first, then today's new ones.

        Cram mode ignores the schedule and returns the whole scope, weakest first."""
        pack = self._load(pack_id)
        states, today = self._progress.states(pack_id), self._clock.today()
        cards = self._in_scope(pack, scope)
        if cram:
            order = sorted(cards, key=lambda c: (states[c.id].interval if c.id in states else -1,
                                                 self._rng.random()))
            return [self._card_record(pack, c, states.get(c.id)) for c in order]
        due = sorted((c for c in cards if c.id in states and states[c.id].due <= today),
                     key=lambda c: states[c.id].due)
        room = max(0, self.new_per_day() - self._new_today(pack_id, states))
        new = [c for c in cards if c.id not in states][:room]
        return [self._card_record(pack, c, states.get(c.id)) for c in due + new]

    def grade(self, pack_id: str, card_id: str, grade: Grade) -> CardRecord:
        pack = self._load(pack_id)
        card = next((c for c in cards_of(pack) if c.id == card_id), None)
        if card is None:
            raise NotFound("That card isn't in the pack any more.")
        today = self._clock.today()
        states = self._progress.states(pack_id)
        before = states.get(card_id)
        after = review(before, card_id, grade, today, pack.event_date)
        self._progress.save_state(pack_id, after)
        self._progress.log_review(pack_id, card_id, grade, today)
        return self._card_record(pack, card, after)

    # ---- multiple choice ------------------------------------------------------------
    def choice(self, pack_id: str, scope: str = SCOPE_ALL) -> ChoiceRecord | None:
        pack = self._load(pack_id)
        pool = [c for c in cards_of(pack) if c.kind in CHOICE_KINDS]
        targets = [c for c in self._in_scope(pack, scope) if c.kind in CHOICE_KINDS]
        if not targets or len({c.front for c in pool}) < 2:
            return None
        states = self._progress.states(pack_id)
        # Lean on cards that are unseen or shaky.
        weights = [1.0 if c.id not in states else 3.0 if states[c.id].lapses and
                   not states[c.id].known else 0.4 if states[c.id].known else 1.0
                   for c in targets]
        target = self._rng.choices(targets, weights)[0]
        q = choice_question(target, pool, self._rng)
        chapter = pack.chapter(q.chapter_id) if q.chapter_id else None
        return ChoiceRecord(q.card_id, q.prompt, q.options, q.answer,
                            chapter.title if chapter else "Glossary")

    def answer_choice(self, pack_id: str, card_id: str, correct: bool) -> None:
        """A wrong pick sends the card back to the start of its schedule; a right one
        only counts towards today's work (recognising isn't the same as recalling)."""
        today = self._clock.today()
        if not correct:
            self.grade(pack_id, card_id, Grade.AGAIN)
        else:
            self._progress.log_review(pack_id, card_id, Grade.GOOD, today, drill=True)

    def reset_progress(self, pack_id: str) -> None:
        self._load(pack_id)
        self._progress.reset(pack_id)

    # ---- reference ----------------------------------------------------------------
    def glossary(self, pack_id: str, query: str = "") -> list[TermRecord]:
        return [TermRecord(t.term, t.definition) for t in self._load(pack_id).glossary
                if _matches(query, t.term, t.definition)]

    def cheatsheet(self, pack_id: str, query: str = "") -> list[CheatRecord]:
        return [CheatRecord(g.section, g.title, g.lines) for g in self._load(pack_id).cheatsheet
                if _matches(query, g.section, g.title, *g.lines)]
