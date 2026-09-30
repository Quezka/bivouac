"""The only place that knows which adapters implement which ports."""
from __future__ import annotations

from .application.ports import Clock, KeyValueStore, ManualReader, PackStore, ProgressStore
from .application.library import LibraryService
from .application.services import Services
from .application.study import StudyService
from .infrastructure.manuals import PdfManualReader
from .infrastructure.packs import JsonPackStore
from .infrastructure.progress import SqliteProgress
from .infrastructure.settings import JsonSettings, SystemClock


def build_services(packs: PackStore | None = None, progress: ProgressStore | None = None,
                   settings: KeyValueStore | None = None, manuals: ManualReader | None = None,
                   clock: Clock | None = None) -> Services:
    packs = packs or JsonPackStore()
    progress = progress or SqliteProgress()
    settings = settings or JsonSettings()
    return Services(
        library=LibraryService(packs, manuals or PdfManualReader(), progress, settings),
        study=StudyService(packs, progress, clock or SystemClock(), settings),
    )
