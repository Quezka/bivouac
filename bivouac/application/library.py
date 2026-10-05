"""Use cases for the pack shelf: import, create, pick, edit, delete; plus school branding."""
from __future__ import annotations

import re
import uuid
from dataclasses import replace
from pathlib import Path

from ..domain.model import CustomCard, Pack, cards_of
from .errors import FileFormatError, InvalidInput, NotFound
from .inputs import BrandingInput, CardInput, PackInput
from .ports import KeyValueStore, ManualReader, PackStore, ProgressStore
from .records import BrandingRecord, PackRecord

DEFAULT_SCHOOL = 'I.T.S. "E. Alessandrini"'
DEFAULT_PLACE = "Montesilvano (PE)"


def pack_record(pack: Pack) -> PackRecord:
    return PackRecord(pack.id, pack.title, pack.subtitle, pack.event, pack.event_date,
                      pack.has_source, len(pack.chapters), len(cards_of(pack)), len(pack.cards))


class LibraryService:
    def __init__(self, packs: PackStore, manuals: ManualReader, progress: ProgressStore,
                 settings: KeyValueStore):
        self._packs = packs
        self._manuals = manuals
        self._progress = progress
        self._settings = settings

    # ---- the shelf ----------------------------------------------------------------
    def packs(self) -> list[PackRecord]:
        return [pack_record(p) for p in sorted(self._packs.list(), key=lambda p: p.title.lower())]

    def active(self) -> PackRecord | None:
        packs = self.packs()
        wanted = self._settings.get("active_pack")
        return next((p for p in packs if p.id == wanted), packs[0] if packs else None)

    def set_active(self, pack_id: str) -> None:
        self._packs.load(pack_id)  # raises NotFound
        self._settings.set("active_pack", pack_id)

    def _unique_id(self, wanted: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", wanted.lower()).strip("-") or "pack"
        taken = {p.id for p in self._packs.list()}
        candidate, n = base, 2
        while candidate in taken:
            candidate, n = f"{base}-{n}", n + 1
        return candidate

    def import_file(self, path: str, replace_existing: bool = True) -> PackRecord:
        """A pack from a JSON pack file or a competition manual (PDF).

        Importing the same material again replaces the pack's content but keeps
        the student's own cards, date and progress.
        """
        suffix = Path(path).suffix.lower()
        if suffix == ".pdf":
            pack, source = self._manuals.read(path), path
        elif suffix == ".json":
            pack, source = self._packs.read_file(path), None
        else:
            raise FileFormatError("Pick a study pack (.json) or a competition manual (.pdf).")
        existing = next((p for p in self._packs.list() if p.id == pack.id), None)
        if existing and replace_existing:
            pack = replace(pack, cards=existing.cards + tuple(
                c for c in pack.cards if c.id not in {e.id for e in existing.cards}),
                event_date=pack.event_date or existing.event_date)
        elif existing:
            pack = replace(pack, id=self._unique_id(pack.id))
        stored = self._packs.save(pack, source)
        self._settings.set("active_pack", stored.id)
        return pack_record(stored)

    def attach_source(self, pack_id: str, pdf_path: str) -> PackRecord:
        if Path(pdf_path).suffix.lower() != ".pdf":
            raise FileFormatError("The original material has to be a PDF.")
        return pack_record(self._packs.save(self._packs.load(pack_id), pdf_path))

    def source_path(self, pack_id: str) -> str | None:
        return self._packs.source_path(pack_id)

    def export(self, pack_id: str, path: str) -> None:
        self._packs.write_file(self._packs.load(pack_id), path)

    def create(self, data: PackInput) -> PackRecord:
        title = data.title.strip()
        if not title:
            raise InvalidInput("Give the pack a name.")
        pack = Pack(self._unique_id(title), title, data.subtitle.strip(), data.event.strip(),
                    data.event_date)
        stored = self._packs.save(pack)
        self._settings.set("active_pack", stored.id)
        return pack_record(stored)

    def update(self, pack_id: str, data: PackInput) -> PackRecord:
        if not data.title.strip():
            raise InvalidInput("Give the pack a name.")
        pack = replace(self._packs.load(pack_id), title=data.title.strip(),
                       subtitle=data.subtitle.strip(), event=data.event.strip(),
                       event_date=data.event_date)
        return pack_record(self._packs.save(pack))

    def delete(self, pack_id: str) -> None:
        self._packs.load(pack_id)
        self._packs.delete(pack_id)
        self._progress.reset(pack_id)

    # ---- the student's own cards ------------------------------------------------------
    def add_card(self, pack_id: str, data: CardInput) -> PackRecord:
        if not data.front.strip() or not data.back.strip():
            raise InvalidInput("A card needs both a question and an answer.")
        pack = self._packs.load(pack_id)
        if data.chapter_id and pack.chapter(data.chapter_id) is None:
            raise NotFound("There's no chapter {id}.", id=data.chapter_id)
        card = CustomCard(uuid.uuid4().hex[:12], data.front.strip(), data.back.strip(),
                          data.chapter_id)
        return pack_record(self._packs.save(replace(pack, cards=pack.cards + (card,))))

    def delete_card(self, pack_id: str, card_id: str) -> PackRecord:
        pack = self._packs.load(pack_id)
        own = card_id.removeprefix("u:")
        return pack_record(self._packs.save(
            replace(pack, cards=tuple(c for c in pack.cards if c.id != own))))

    # ---- branding -----------------------------------------------------------------
    def branding(self) -> BrandingRecord:
        return BrandingRecord(self._settings.get("school") or DEFAULT_SCHOOL,
                              self._settings.get("place") or DEFAULT_PLACE,
                              self._settings.get("school_logo") or None)

    def set_branding(self, data: BrandingInput) -> BrandingRecord:
        self._settings.set("school", data.school.strip() or None)
        self._settings.set("place", data.place.strip() or None)
        self._settings.set("school_logo", data.logo or None)
        return self.branding()
