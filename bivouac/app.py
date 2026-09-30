"""Command-line entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bootstrap import build_services


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(prog="bivouac",
                                     description="Base camp for CTF study.")
    parser.add_argument("--import", dest="source", type=Path,
                        help="import a competition manual (.pdf) or study pack (.json) first")
    args, qt_args = parser.parse_known_args(argv[1:])

    services = build_services()
    if args.source:
        from .application.errors import ApplicationError
        try:
            pack = services.library.import_file(str(args.source))
            print(f"Imported {pack.title}: {pack.chapter_count} chapters, {pack.card_count} cards")
        except ApplicationError as e:
            print(f"bivouac: {e}", file=sys.stderr)
            return 1
    # Imported late so `--help` and `--import` work without a display.
    from .presentation.qt_app import run

    return run(services, [argv[0], *qt_args])
