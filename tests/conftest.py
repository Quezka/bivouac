import os
import random
from datetime import date, datetime

import pytest

os.environ.setdefault("QT_SCALE_FACTOR", "1")  # tests measure pixels: no automatic scaling

from bivouac.application.library import LibraryService
from bivouac.application.services import Services
from bivouac.application.study import StudyService
from bivouac.application.updates import UpdateService
from bivouac.infrastructure.packs import JsonPackStore
from bivouac.infrastructure.progress import SqliteProgress
from bivouac.infrastructure.settings import MemorySettings

from .fakes import FakeInstaller, FakeManuals, FakeReleases, sample_pack_dict


class Clock:
    """Today's date for studying; called, the time of day for update checks."""

    def __init__(self):
        self.day = date(2026, 10, 1)
        self.now = datetime(2026, 10, 1, 10, 0)

    def today(self):
        return self.day

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def releases():
    return FakeReleases()


@pytest.fixture
def installer():
    return FakeInstaller()


@pytest.fixture
def services(tmp_path, clock, releases, installer):
    packs = JsonPackStore(tmp_path / "packs")
    progress = SqliteProgress(":memory:")
    settings = MemorySettings()
    return Services(
        library=LibraryService(packs, FakeManuals(), progress, settings),
        study=StudyService(packs, progress, clock, settings, random.Random(7)),
        updates=UpdateService(releases, installer, settings, "0.1.0", clock),
    )


@pytest.fixture
def pack_file(tmp_path):
    import json
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(sample_pack_dict()), encoding="utf-8")
    return path


@pytest.fixture
def pack(services, pack_file):
    return services.library.import_file(str(pack_file))


@pytest.fixture(scope="session", autouse=True)
def empty_clipboard():
    """Qt's headless platform can crash at exit if the clipboard still holds data."""
    yield
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return
    app = QApplication.instance()
    if app is not None:
        app.clipboard().clear()


@pytest.fixture(autouse=True)
def full_hd_screen(monkeypatch):
    """The headless test screen is tiny; windows are clamped to the screen, so pretend it is
    a normal one (the clamp itself is tested in test_uiscale)."""
    try:
        from PySide6.QtCore import QRect
        from bivouac.presentation import fit
    except ImportError:
        return
    monkeypatch.setattr(fit, "available", lambda widget=None: QRect(0, 0, 1920, 1040))
