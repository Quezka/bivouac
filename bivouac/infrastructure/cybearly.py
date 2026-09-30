"""Turns a Cybearly "Campo base" manual (as `pdftotext -layout` text) into a study pack.

The manual is laid out the same way in every chapter: numbered sections, then a recap
with "Cosa è stato imparato" bullets, a "Concetti chiave in tabella" table, resources and
a "Mini-quiz di autovalutazione". Appendix A is a cheatsheet, Appendix B a glossary.
The result is a plain dict in the pack JSON format (see `packs.py`).
"""
from __future__ import annotations

import re

_WATERMARK = re.compile(r"\S*\|[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}\|\S*|(Emilio )?Alessandrini di "
                        r"Montesilvano|onavlisetnoM id inirdnasselA( oilimE)?|\s{8,}\d{1,3}$")
_NOISE = ("S.r.l.", "Sede legale", "Ufficio di Milano", "Partita IVA", "Copia ad uso didattico",
          "Cybearly Challenge - Tutti", "www.cybearly.com", "info@bearit.com", "www.bearit.com",
          "(+39)")
_DOTS = re.compile(r"\s*\.{4,}\s*\d*\s*$")
_CHAPTER = re.compile(r"^\s*Capitolo (\d\.\d|R\d): (.+?)\s*$")
_PART = re.compile(r"^\s*PARTE (\d): (.+?)\s*$")
_SECTION = re.compile(r"^\s*((?:\d\.\d|R\d)\.\d+): (.+?)\s*$")
_APPENDIX = re.compile(r"^\s*Appendice ([A-F]): (.+?)\s*$")
_RECAP = re.compile(r"^\s*Cosa (hai|è stato) imparato\s*$")
_BULLET = "•"


def clean_lines(text: str) -> tuple[list[str], list[int]]:
    """Drop page furniture (footers, watermarks, page numbers) but keep the columns.

    Also returns the 0-based PDF page each line came from.
    """
    lines, pages = [], []
    for page, chunk in enumerate(text.split("\f")):
        for raw in chunk.splitlines():
            line = raw.rstrip()
            if line.strip().startswith(_NOISE):
                line = ""
            # The licence watermark runs through real text: blank it but keep the columns.
            line = _WATERMARK.sub(lambda m: " " * len(m.group(0)), line).rstrip()
            if re.fullmatch(r"\d{1,3}", line.strip()):
                line = ""
            lines.append(line)
            pages.append(page)
    return lines, pages


def _join(parts: list[str]) -> str:
    text = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if text.endswith("-") and not text.endswith(" -") and part[:1].islower():
            text = text[:-1] + part  # a word hyphenated across lines
        else:
            text = f"{text} {part}" if text else part
    return text


def _bullets(lines: list[str]) -> list[str]:
    items: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(_BULLET):
            items.append([stripped[1:]])
        elif re.fullmatch(r"[A-Z]", stripped):  # a letter heading in the glossary
            items.append([])
        elif stripped and items:
            items[-1].append(stripped)
    return [t for t in (_join(i) for i in items) if t]


def _groups(lines: list[str]) -> list[list[str]]:
    groups, current = [], []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def _table(lines: list[str]) -> list[dict]:
    """A table laid out in columns; rows are blocks separated by blank lines."""
    groups = _groups(lines)
    if not groups:
        return [], []
    header_at, header = 0, list(groups[0])
    # Some headers put each cell on its own line, a blank line apart.
    while len(header) == 1 and len(header[0].split()) <= 3 and header_at + 1 < len(groups) \
            and len(groups[header_at + 1]) == 1 and len(header) < 3:
        header_at += 1
        header += groups[header_at]
    starts: list[int] = []  # header cells can sit on different lines
    for pos in sorted(m.start() for line in header
                      for m in re.finditer(r"(?<!\S)\S+(?: \S+)*", line)):
        if not starts or pos - starts[-1] > 4:
            starts.append(pos)
    if len(starts) < 2:
        return [], []
    names = [_join([l[max(0, s - 3):(starts[i + 1] - 3 if i + 1 < len(starts) else None)]
                    for l in header]) for i, s in enumerate(starts)]
    # Cells don't always line up with their header (some are shifted a few characters
    # left), so cut each column where every row has a space, at or before the header.
    body = [l for g in groups[header_at + 1:] for l in g]

    def clear_at(c: int) -> bool:
        return all(len(l) < c or l[c - 1] == " " for l in body)

    bounds = [0]
    for prev, s in zip(starts, starts[1:]):
        bounds.append(next((c for c in range(s, prev + 1, -1) if clear_at(c)), s - 3))
    bounds.append(10_000)
    rows: list[list[str]] = []
    for group in groups[header_at + 1:]:
        cells = [_join([l[bounds[i]:bounds[i + 1]] for l in group]) for i in range(len(starts))]
        if not any(cells):
            continue
        if not cells[0] and rows:  # a row broken by a page: carry on with the last one
            rows[-1] = [_join([a, b]) for a, b in zip(rows[-1], cells)]
        else:
            rows.append(cells)
    keys = ("term", "meaning", "example")
    return names[:3], [{k: v for k, v in zip(keys, row) if v}
                       for row in rows if row[0] and any(row[1:])]


def _quiz(lines: list[str]) -> list[dict]:
    items, mode = [], None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\d+\.\s", stripped):
            items.append({"q": [re.sub(r"^\d+\.\s*", "", stripped)], "a": []})
            mode = "q"
        elif stripped.startswith("Risposta") and items:
            items[-1]["a"].append(re.sub(r"^Risposta\.?\s*", "", stripped))
            mode = "a"
        elif items and mode:
            items[-1][mode].append(stripped)
    return [{"question": _join(i["q"]), "answer": _join(i["a"])} for i in items if i["a"]]


def _between(lines, start, end_patterns):
    for j in range(start, len(lines)):
        if any(p.match(lines[j]) for p in end_patterns):
            return lines[start:j], j
    return lines[start:], len(lines)


def _chapter(chapter_id: str, title: str, part: str, body: list[str],
             pages: list[int]) -> dict:
    heads = {
        "recap": _RECAP, "concepts": re.compile(r"^\s*Concetti chiave in tabella\s*$"),
        "resources": re.compile(r"^\s*Risorse per approfondire\s*$"),
        "quiz": re.compile(r"^\s*Mini-quiz di autovalutazione\s*$"),
        "end": re.compile(r"^\s*Capitolo completato"),
        "recap_title": re.compile(r"^\s*(📚\s*)?Recap del Capitolo"),
    }
    where = {k: next((i for i, l in enumerate(body) if p.match(l)), None) for k, p in heads.items()}
    order = sorted((i, k) for k, i in where.items() if i is not None)

    def span(key):
        if where[key] is None:
            return []
        after = [i for i, _k in order if i > where[key]]
        return body[where[key] + 1: after[0] if after else len(body)]

    main_end = where["recap_title"] or where["recap"] or len(body)
    blurb_lines, _ = _between(body, 1, [re.compile(r"^\s*$")])
    sections, current = [], None
    for n, line in enumerate(body[1:main_end], start=1):
        m = _SECTION.match(line)
        if m and m.group(1).startswith(chapter_id):
            sections.append({"title": f"{m.group(1)} {m.group(2)}", "page": pages[n]})
    if where["recap_title"] is not None:
        sections.append({"title": "Recap", "page": pages[where["recap_title"]]})
    headers, concepts = _table(span("concepts"))
    return {
        "id": chapter_id,
        "part": part,
        "title": title,
        "blurb": _join(blurb_lines),
        "summary": _bullets(span("recap")),
        "concept_headers": headers,
        "concepts": concepts,
        "resources": _bullets(span("resources")),
        "quiz": _quiz(span("quiz")),
        "page": pages[0],
        "sections": sections,
    }


def _glossary(lines: list[str]) -> list[dict]:
    terms = []
    for item in _bullets(lines):
        depth, cut = 0, None
        for i, ch in enumerate(item):
            depth += ch == "("
            depth -= ch == ")"
            if ch == "." and depth == 0 and item[i + 1:i + 2] in (" ", ""):
                cut = i
                break
        if cut is None or cut > 80:
            continue
        terms.append({"term": item[:cut].strip(), "definition": item[cut + 1:].strip()})
    return terms


def _cheatsheet(lines: list[str]) -> list[dict]:
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    base = min(indents) if indents else 0
    groups, section = [], ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"^A\.\d+: (.+)$", stripped)
        if m and indent < base + 8:
            section = m.group(1)
        elif indent < base + 8:
            if groups and groups[-1]["section"] == section and not groups[-1]["lines"]:
                groups[-1]["title"] = _join([groups[-1]["title"], stripped])
            else:
                groups.append({"section": section, "title": stripped, "lines": []})
        elif groups:
            groups[-1]["lines"].append(stripped)
    return [g for g in groups if g["lines"]]


def parse_manual(text: str, pack_id: str = "cybearly-2027") -> dict:
    lines, pages = clean_lines(text)
    toc_titles: dict[str, str] = {}
    first_body = None
    for i, line in enumerate(lines):
        m = _CHAPTER.match(line)
        if m and _DOTS.search(line):
            toc_titles.setdefault(m.group(1), _DOTS.sub("", m.group(2)).strip())
        elif m and toc_titles and first_body is None:
            first_body = i
    if first_body:  # start at the part heading just above the first chapter
        first_body = next((j for j in range(first_body, max(first_body - 60, 0), -1)
                           if _PART.match(lines[j])), first_body)
    body, pages = lines[first_body or 0:], pages[first_body or 0:]

    chapters, part, starts = [], "", []
    for i, line in enumerate(body):
        pm, cm, am = _PART.match(line), _CHAPTER.match(line), _APPENDIX.match(line)
        if pm:
            part = pm.group(2).title()
            starts.append((i, "part", pm.group(2)))
        elif cm and cm.group(1) in toc_titles and cm.group(1) not in {s[2] for s in starts}:
            starts.append((i, "chapter", cm.group(1), part))
        elif am and not _DOTS.search(line):
            starts.append((i, "appendix", am.group(1)))
    starts.append((len(body), "end", ""))

    appendix: dict[str, list[str]] = {}
    for n, entry in enumerate(starts[:-1]):
        chunk = body[entry[0]:starts[n + 1][0]]
        if entry[1] == "chapter":
            chapters.append(_chapter(entry[2], toc_titles[entry[2]], entry[3], chunk,
                                     pages[entry[0]:starts[n + 1][0]]))
        elif entry[1] == "appendix":
            appendix[entry[2]] = appendix.get(entry[2], []) + chunk[1:]
    return {
        "format": 1,
        "id": pack_id,
        "title": "Cybearly 2027 — Campo base",
        "subtitle": "Manuale operativo Mirror Match",
        "event": "Cybearly 2027",
        "language": "it",
        "chapters": chapters,
        "glossary": _glossary(appendix.get("B", [])),
        "cheatsheet": _cheatsheet(appendix.get("A", [])),
        "cards": [],
    }
