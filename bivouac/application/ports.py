"""What the use cases need from the outside world; adapters live in `infrastructure`."""
from __future__ import annotations

from datetime import date
from typing import Protocol

from ..domain.model import Pack
from ..domain.srs import Grade, ReviewState


class PackStore(Protocol):
    def list(self) -> list[Pack]: ...

    def load(self, pack_id: str) -> Pack:
        """Raises NotFound."""

    def save(self, pack: Pack, source_pdf: str | None = None) -> Pack:
        """Stores the pack (and a copy of its source PDF); returns it as stored."""

    def delete(self, pack_id: str) -> None: ...

    def source_path(self, pack_id: str) -> str | None: ...

    def read_file(self, path: str) -> Pack:
        """A pack from a JSON file. Raises FileFormatError / FileAccessError."""

    def write_file(self, pack: Pack, path: str) -> None: ...


class ManualReader(Protocol):
    def read(self, pdf_path: str) -> Pack:
        """A pack from a competition manual in PDF. Raises FileFormatError."""


class ProgressStore(Protocol):
    def states(self, pack_id: str) -> dict[str, ReviewState]: ...

    def save_state(self, pack_id: str, state: ReviewState) -> None: ...

    def log_review(self, pack_id: str, card_id: str, grade: Grade, day: date,
                   drill: bool = False) -> None:
        """Remember an answer; drill answers (multiple choice) never count as first sights."""

    def reviews_by_day(self, pack_id: str, since: date) -> dict[date, int]: ...

    def first_seen_on(self, pack_id: str, day: date) -> int:
        """How many cards had their very first review that day."""

    def read_chapters(self, pack_id: str) -> set[str]: ...

    def set_read(self, pack_id: str, chapter_id: str, read: bool) -> None: ...

    def reset(self, pack_id: str) -> None: ...


class KeyValueStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str | None) -> None: ...


class Clock(Protocol):
    def today(self) -> date: ...
