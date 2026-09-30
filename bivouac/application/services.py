"""Everything the UI can ask for, in one place (built by `bootstrap`)."""
from __future__ import annotations

from dataclasses import dataclass

from .library import LibraryService
from .study import StudyService
from .updates import AvailableUpdate, UpdateService


@dataclass
class Services:
    library: LibraryService
    study: StudyService
    updates: UpdateService


__all__ = ["AvailableUpdate", "Services"]
