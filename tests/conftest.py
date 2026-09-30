import random
from datetime import date

import pytest

from bivouac.application.library import LibraryService
from bivouac.application.services import Services
from bivouac.application.study import StudyService
from bivouac.infrastructure.packs import JsonPackStore
from bivouac.infrastructure.progress import SqliteProgress
from bivouac.infrastructure.settings import MemorySettings

from .fakes import FakeManuals, sample_pack_dict


class Clock:
    def __init__(self):
        self.day = date(2026, 10, 1)

    def today(self):
        return self.day


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def services(tmp_path, clock):
    packs = JsonPackStore(tmp_path / "packs")
    progress = SqliteProgress(":memory:")
    settings = MemorySettings()
    return Services(
        library=LibraryService(packs, FakeManuals(), progress, settings),
        study=StudyService(packs, progress, clock, settings, random.Random(7)),
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
