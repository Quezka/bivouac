# Bivouac

Python 3.10+ / PySide6 desktop app for CTF study (flashcards, drills, chapters, cheatsheet).
Sibling of Quire (`../quire`) and Ligature (`../ligature`): same look, same toolkit, but in
the school's colours (I.T.S. "E. Alessandrini", Montesilvano: blue `#0066ff`, navy `#000080`,
red `#aa0000`; emblem in `bivouac/assets/school.png`).

- Layers: `bivouac/domain` → `bivouac/application` → `bivouac/infrastructure` + `bivouac/presentation`; wired in `bivouac/bootstrap.py`. `tests/test_architecture.py` enforces it; the UI never imports the domain (enums via `application/types.py`).
- Run: `.venv/bin/bivouac`. Test: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`.
- The venv has no pip of its own (no python3-venv on this machine): install with `../quire/.venv/bin/pip --python .venv/bin/python install …`.
- A pack is one JSON file (format documented in `infrastructure/packs.py`) plus an optional `<id>.pdf`. Card ids derive from content (`k:<chapter>:<slug>`, `q:<chapter>:<n>`, `g:<slug>`, `u:<id>`) so re-importing a manual keeps progress.
- `infrastructure/cybearly.py` parses `pdftotext -layout` output of the Cybearly "Campo base" manual. Tests use the made-up text in `tests/fakes.py`; **never commit real manual text or packs** (the manual is licensed to the school).
- UI text: wrap in `_()`/`N_()`, add Russian and Italian to `presentation/locales/ru.py` and `it.py` (`tests/test_i18n.py`); study content stays in the pack's language. Errors raised by the application/infrastructure layers are English templates with keyword values (`NotFound("There's no chapter {id}.", id=...)`); the UI translates them with `common.error_text`. Never use `_` as a variable.
