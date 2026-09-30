"""Reads a competition manual (PDF) into a pack, via poppler's `pdftotext`."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ..application.errors import FileAccessError, FileFormatError
from ..domain.model import Pack
from .cybearly import parse_manual
from .packs import pack_from_dict


def pdf_text(path: str) -> str:
    tool = shutil.which("pdftotext")
    if tool is None:
        raise FileAccessError("Reading PDFs needs pdftotext (install the poppler-utils package).")
    try:
        done = subprocess.run([tool, "-layout", "-enc", "UTF-8", path, "-"], capture_output=True,
                              timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise FileAccessError(f"{Path(path).name} couldn't be read: {e}") from None
    if done.returncode != 0:
        raise FileFormatError(f"{Path(path).name} isn't a readable PDF.")
    return done.stdout.decode("utf-8", errors="replace")


class PdfManualReader:
    def read(self, pdf_path: str) -> Pack:
        data = parse_manual(pdf_text(pdf_path), pack_id=_pack_id(pdf_path))
        if not data["chapters"]:
            raise FileFormatError(
                "Bivouac found no chapters in this PDF. It reads Cybearly \"Campo base\" "
                "manuals; for other material, make a pack and add your own cards.")
        return pack_from_dict(data)


def _pack_id(pdf_path: str) -> str:
    """Cybearly 2027 -> "cybearly-2027", so a newer copy of the same manual replaces the old."""
    match = re.search(r"cybearly\s*(\d{4})", Path(pdf_path).name, re.IGNORECASE)
    return f"cybearly-{match.group(1)}" if match else "cybearly"
