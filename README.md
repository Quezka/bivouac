# Bivouac

Base camp for CTF study. Bivouac turns competition material into something you can
practise with every day: chapter recaps, spaced-repetition flashcards, a multiple-choice
drill, a searchable glossary and command cheatsheet, and the manual itself one click away.

Made for the students of **I.T.S. "E. Alessandrini", Montesilvano** preparing for
Cybearly 2027, and usable for any other competition (OliCyber, CyberChallenge, …).

## Run

```sh
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/bivouac                     # or: .venv/bin/bivouac --import manual.pdf
```

Reading PDFs needs `pdftotext` (the `poppler-utils` package).

## Study packs

Everything you study lives in a *pack*, one per competition, kept in
`~/.local/share/Bivouac/packs/` (progress in `progress.db` next to it).

- **Import a Cybearly "Campo base" manual** (More → Import manual or pack…): Bivouac
  reads every chapter's recap, key-concept table and mini-quiz, the glossary and the
  cheatsheet, and keeps a copy of the PDF so chapters open at the right page.
- **Start an empty pack** for another competition and add cards as you learn
  (Practice → Add card, or Ctrl+Shift+N).
- **Write a pack by hand** as JSON and import it: the format is documented at the top of
  [`bivouac/infrastructure/packs.py`](bivouac/infrastructure/packs.py). Only `title` is
  required.

Packs made from competition material are for your own study: the material belongs to its
authors, so don't publish or share them. `.gitignore` keeps PDFs and packs out of this repo.

## How it schedules cards

A small SM-2: *Again* brings a card back in the same session, *Good* spaces it 1, 3, then
about 2.5× the last gap in days. With a competition date set, no gap is longer than half the
time left, so every card comes round again before the day. New cards are capped per day
(20 by default, in Settings).

## Keys

| | |
|---|---|
| Ctrl+1 … Ctrl+7 | Overview, Chapters, Digest, Practice, Glossary, Cheatsheet, Manual |
| Space | Show answer / next question |
| 1 2 3 4 | Again · Hard · Good · Easy — or pick an option |
| R · P · O | Chapter: mark read · practise · open in manual |
| Ctrl+F | Search the glossary or cheatsheet |

## Development

Clean Architecture, as in Quire and Ligature: `domain` → `application` → `infrastructure`
and `presentation`, wired in `bootstrap.py`, enforced by `tests/test_architecture.py`.

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

GPL-3.0-or-later.
