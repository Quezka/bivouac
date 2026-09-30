"""Study packs as JSON files in the data folder, each with an optional copy of its PDF.

Pack format (version 1), easy to write by hand for any competition:

    {"format": 1, "id": "olicyber-2027", "title": "OliCyber 2027", "event": "OliCyber",
     "event_date": "2027-03-14",
     "chapters": [{"id": "1", "title": "Crypto", "part": "", "blurb": "", "page": null,
                   "summary": ["..."], "concept_headers": ["Termine", "Significato"],
                   "concepts": [{"term": "XOR", "meaning": "...", "example": "..."}],
                   "resources": ["..."], "quiz": [{"question": "...", "answer": "..."}],
                   "sections": [{"title": "1.1 ...", "page": 3}]}],
     "glossary": [{"term": "...", "definition": "..."}],
     "cheatsheet": [{"section": "...", "title": "...", "lines": ["nmap -sV target"]}],
     "cards": [{"id": "a1", "front": "...", "back": "...", "chapter_id": "1"}]}

Only "title" is required; everything else defaults to empty.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

from ..application.errors import FileAccessError, FileFormatError, NotFound
from ..domain.model import (
    Chapter, CheatGroup, Concept, CustomCard, Pack, QuizItem, Section, Term, slug,
)

FORMAT = 1


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "Bivouac"


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _texts(value) -> tuple[str, ...]:
    return tuple(t for t in (_text(v) for v in value) if t) if isinstance(value, list) else ()


def _page(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _list(value) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def pack_from_dict(data, has_source: bool = False) -> Pack:
    if not isinstance(data, dict) or not _text(data.get("title")):
        raise FileFormatError("This isn't a Bivouac study pack (it has no title).")
    if isinstance(data.get("format"), int) and data["format"] > FORMAT:
        raise FileFormatError("This pack was made by a newer Bivouac. Update to open it.")
    try:
        event_date = date.fromisoformat(data["event_date"]) if data.get("event_date") else None
    except (TypeError, ValueError):
        event_date = None
    chapters = []
    for n, c in enumerate(_list(data.get("chapters")), start=1):
        chapters.append(Chapter(
            id=_text(c.get("id")) or str(n), title=_text(c.get("title")) or f"Chapter {n}",
            part=_text(c.get("part")), blurb=_text(c.get("blurb")), page=_page(c.get("page")),
            summary=_texts(c.get("summary")), concept_headers=_texts(c.get("concept_headers")),
            concepts=tuple(Concept(_text(k.get("term")), _text(k.get("meaning")),
                                   _text(k.get("example")))
                           for k in _list(c.get("concepts")) if _text(k.get("term"))),
            resources=_texts(c.get("resources")),
            quiz=tuple(QuizItem(_text(q.get("question")), _text(q.get("answer")))
                       for q in _list(c.get("quiz")) if _text(q.get("question"))),
            sections=tuple(Section(_text(s.get("title")), _page(s.get("page")))
                           for s in _list(c.get("sections")) if _text(s.get("title"))),
        ))
    return Pack(
        id=slug(_text(data.get("id")) or _text(data.get("title"))) or "pack",
        title=_text(data["title"]), subtitle=_text(data.get("subtitle")),
        event=_text(data.get("event")), event_date=event_date,
        language=_text(data.get("language")), chapters=tuple(chapters),
        glossary=tuple(Term(_text(t.get("term")), _text(t.get("definition")))
                       for t in _list(data.get("glossary")) if _text(t.get("term"))),
        cheatsheet=tuple(CheatGroup(_text(g.get("section")), _text(g.get("title")),
                                    tuple(str(l) for l in g.get("lines", [])
                                          if isinstance(l, str)))
                         for g in _list(data.get("cheatsheet"))),
        cards=tuple(CustomCard(_text(k.get("id")) or str(i), _text(k.get("front")),
                               _text(k.get("back")), _text(k.get("chapter_id")))
                    for i, k in enumerate(_list(data.get("cards")))),
        has_source=has_source,
    )


def pack_to_dict(pack: Pack) -> dict:
    return {
        "format": FORMAT, "id": pack.id, "title": pack.title, "subtitle": pack.subtitle,
        "event": pack.event,
        "event_date": pack.event_date.isoformat() if pack.event_date else None,
        "language": pack.language,
        "chapters": [{
            "id": c.id, "title": c.title, "part": c.part, "blurb": c.blurb, "page": c.page,
            "summary": list(c.summary), "concept_headers": list(c.concept_headers),
            "concepts": [{"term": k.term, "meaning": k.meaning, "example": k.example}
                         for k in c.concepts],
            "resources": list(c.resources),
            "quiz": [{"question": q.question, "answer": q.answer} for q in c.quiz],
            "sections": [{"title": s.title, "page": s.page} for s in c.sections],
        } for c in pack.chapters],
        "glossary": [{"term": t.term, "definition": t.definition} for t in pack.glossary],
        "cheatsheet": [{"section": g.section, "title": g.title, "lines": list(g.lines)}
                       for g in pack.cheatsheet],
        "cards": [{"id": k.id, "front": k.front, "back": k.back, "chapter_id": k.chapter_id}
                  for k in pack.cards],
    }


class JsonPackStore:
    def __init__(self, folder: Path | None = None):
        self._dir = folder or data_dir() / "packs"

    def _json(self, pack_id: str) -> Path:
        return self._dir / f"{pack_id}.json"

    def _pdf(self, pack_id: str) -> Path:
        return self._dir / f"{pack_id}.pdf"

    def list(self) -> list[Pack]:
        found = []
        for path in sorted(self._dir.glob("*.json")) if self._dir.is_dir() else []:
            try:
                found.append(self.load(path.stem))
            except (FileFormatError, NotFound):
                continue  # a broken file shouldn't hide the others
        return found

    def load(self, pack_id: str) -> Pack:
        path = self._json(pack_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise NotFound("That study pack isn't there any more.") from None
        except (OSError, ValueError) as e:
            raise FileFormatError(f"The pack {path.name} can't be read: {e}") from None
        return replace(pack_from_dict(data, self._pdf(pack_id).is_file()), id=pack_id)

    def save(self, pack: Pack, source_pdf: str | None = None) -> Pack:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            if source_pdf and Path(source_pdf).resolve() != self._pdf(pack.id).resolve():
                shutil.copyfile(source_pdf, self._pdf(pack.id))
            tmp = self._json(pack.id).with_suffix(".tmp")
            tmp.write_text(json.dumps(pack_to_dict(pack), ensure_ascii=False, indent=1),
                           encoding="utf-8")
            tmp.replace(self._json(pack.id))
        except OSError as e:
            raise FileAccessError(f"The pack couldn't be saved: {e.strerror or e}") from None
        return self.load(pack.id)

    def delete(self, pack_id: str) -> None:
        for path in (self._json(pack_id), self._pdf(pack_id)):
            path.unlink(missing_ok=True)

    def source_path(self, pack_id: str) -> str | None:
        path = self._pdf(pack_id)
        return str(path) if path.is_file() else None

    def read_file(self, path: str) -> Pack:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as e:
            raise FileAccessError(f"{Path(path).name} can't be opened: {e.strerror or e}") from None
        except ValueError:
            raise FileFormatError(f"{Path(path).name} isn't a study pack (not valid JSON).") \
                from None
        return pack_from_dict(data)

    def write_file(self, pack: Pack, path: str) -> None:
        try:
            Path(path).write_text(json.dumps(pack_to_dict(pack), ensure_ascii=False, indent=1),
                                  encoding="utf-8")
        except OSError as e:
            raise FileAccessError(f"The pack couldn't be saved: {e.strerror or e}") from None
