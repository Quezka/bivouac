"""Study progress (card schedules, answer log, chapters read) in SQLite."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from ..domain.srs import Grade, ReviewState
from .packs import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS card_state (
    pack TEXT NOT NULL, card TEXT NOT NULL, due TEXT NOT NULL, interval INTEGER NOT NULL,
    ease REAL NOT NULL, reps INTEGER NOT NULL, lapses INTEGER NOT NULL,
    PRIMARY KEY (pack, card));
CREATE TABLE IF NOT EXISTS review_log (
    id INTEGER PRIMARY KEY, pack TEXT NOT NULL, card TEXT NOT NULL, day TEXT NOT NULL,
    grade INTEGER NOT NULL, drill INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS review_log_pack_day ON review_log (pack, day);
CREATE TABLE IF NOT EXISTS chapter_read (
    pack TEXT NOT NULL, chapter TEXT NOT NULL, PRIMARY KEY (pack, chapter));
"""


class SqliteProgress:
    def __init__(self, path: Path | str | None = None):
        if path is None:
            path = data_dir() / "progress.db"
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.executescript(SCHEMA)

    def states(self, pack_id: str) -> dict[str, ReviewState]:
        rows = self._db.execute(
            "SELECT card, due, interval, ease, reps, lapses FROM card_state WHERE pack = ?",
            (pack_id,))
        return {card: ReviewState(card, date.fromisoformat(due), interval, ease, reps, lapses)
                for card, due, interval, ease, reps, lapses in rows}

    def save_state(self, pack_id: str, state: ReviewState) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO card_state VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pack_id, state.card_id, state.due.isoformat(), state.interval, state.ease,
                 state.reps, state.lapses))

    def log_review(self, pack_id: str, card_id: str, grade: Grade, day: date,
                   drill: bool = False) -> None:
        with self._db:
            self._db.execute(
                "INSERT INTO review_log (pack, card, day, grade, drill) VALUES (?, ?, ?, ?, ?)",
                (pack_id, card_id, day.isoformat(), grade.value, int(drill)))

    def reviews_by_day(self, pack_id: str, since: date) -> dict[date, int]:
        rows = self._db.execute(
            "SELECT day, COUNT(*) FROM review_log WHERE pack = ? AND day >= ? GROUP BY day",
            (pack_id, since.isoformat()))
        return {date.fromisoformat(day): count for day, count in rows}

    def first_seen_on(self, pack_id: str, day: date) -> int:
        (count,) = self._db.execute(
            "SELECT COUNT(*) FROM (SELECT MIN(day) AS first FROM review_log "
            "WHERE pack = ? AND drill = 0 GROUP BY card) WHERE first = ?",
            (pack_id, day.isoformat())).fetchone()
        return count

    def read_chapters(self, pack_id: str) -> set[str]:
        return {c for (c,) in self._db.execute(
            "SELECT chapter FROM chapter_read WHERE pack = ?", (pack_id,))}

    def set_read(self, pack_id: str, chapter_id: str, read: bool) -> None:
        with self._db:
            if read:
                self._db.execute("INSERT OR IGNORE INTO chapter_read VALUES (?, ?)",
                                 (pack_id, chapter_id))
            else:
                self._db.execute("DELETE FROM chapter_read WHERE pack = ? AND chapter = ?",
                                 (pack_id, chapter_id))

    def reset(self, pack_id: str) -> None:
        with self._db:
            for table in ("card_state", "review_log", "chapter_read"):
                self._db.execute(f"DELETE FROM {table} WHERE pack = ?", (pack_id,))
