"""Editors: pack details, a card of your own, settings, about."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate, QSettings, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout,
)

from .. import APP_NAME, HOMEPAGE, __version__
from ..application.errors import ApplicationError
from ..application.inputs import BrandingInput, CardInput, PackInput
from ..application.services import Services
from . import theme
from .common import Segmented, button, error, label, logo_tile
from .icons import APP_ICON, SCHOOL_EMBLEM


def _buttons(dialog: QDialog, ok_text: str = "Save") -> QDialogButtonBox:
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    ok = box.button(QDialogButtonBox.Ok)
    ok.setText(ok_text)
    ok.setObjectName("primary")
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


class PackDialog(QDialog):
    """New pack, or the details of the current one (name, competition, date)."""

    def __init__(self, services: Services, pack=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack = pack
        self.result_pack = None
        self.setWindowTitle("Edit pack" if pack else "New study pack")
        self.setMinimumWidth(480)
        col = QVBoxLayout(self)
        col.setSpacing(12)
        self.name = QLineEdit(objectName="titleEdit", placeholderText="Pack name, e.g. OliCyber 2027")
        self.event = QLineEdit(placeholderText="Competition, e.g. Cybearly 2027 finals")
        self.subtitle = QLineEdit(placeholderText="Optional note")
        self.has_date = QCheckBox("Competition day")
        self.date = QDateEdit(calendarPopup=True, displayFormat="d MMM yyyy")
        self.date.setDate(QDate.currentDate().addDays(30))
        self.has_date.toggled.connect(self.date.setEnabled)
        date_row = QHBoxLayout()
        date_row.addWidget(self.date)
        for text, days in (("In 2 weeks", 14), ("In a month", 30), ("In 3 months", 91)):
            quick = button(text)
            quick.clicked.connect(lambda _c=False, d=days: (
                self.has_date.setChecked(True),
                self.date.setDate(QDate.currentDate().addDays(d))))
            date_row.addWidget(quick)
        date_row.addStretch()
        col.addWidget(self.name)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Competition", self.event)
        form.addRow(self.has_date, date_row)
        form.addRow("Note", self.subtitle)
        col.addLayout(form)
        col.addWidget(label("With a date set, the countdown shows on the home page and the "
                            "flashcard schedule makes sure every card comes back before the day.",
                            "hint", wrap=True))
        col.addWidget(_buttons(self, "Save" if pack else "Create"))
        if pack:
            self.name.setText(pack.title)
            self.event.setText(pack.event)
            self.subtitle.setText(pack.subtitle)
            if pack.event_date:
                self.date.setDate(QDate(pack.event_date.year, pack.event_date.month,
                                        pack.event_date.day))
        self.has_date.setChecked(bool(pack and pack.event_date))
        self.date.setEnabled(self.has_date.isChecked())

    def accept(self):
        d = self.date.date()
        data = PackInput(self.name.text(), self.event.text(),
                         date(d.year(), d.month(), d.day()) if self.has_date.isChecked() else None,
                         self.subtitle.text())
        try:
            self.result_pack = (self.services.library.update(self.pack.id, data) if self.pack
                                else self.services.library.create(data))
        except ApplicationError as e:
            error(self, e)
            return
        super().accept()


class CardDialog(QDialog):
    def __init__(self, services: Services, pack_id: str, chapter_id: str = "", parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = pack_id
        self.setWindowTitle("New card")
        self.setMinimumWidth(520)
        col = QVBoxLayout(self)
        col.setSpacing(10)
        self.front = QLineEdit(objectName="titleEdit",
                               placeholderText="Question or term, e.g. What does nmap -sS do?")
        self.back = QPlainTextEdit(placeholderText="Answer")
        self.back.setFixedHeight(120)
        self.chapter = QComboBox()
        self.chapter.addItem("No chapter", "")
        for c in services.study.chapters(pack_id):
            self.chapter.addItem(f"{c.id} · {c.title}", c.id)
        self.chapter.setCurrentIndex(max(0, self.chapter.findData(chapter_id)))
        self.again = QCheckBox("Add another after this one")
        col.addWidget(self.front)
        col.addWidget(self.back)
        row = QHBoxLayout()
        row.addWidget(label("Chapter", "muted"))
        row.addWidget(self.chapter, 1)
        col.addLayout(row)
        col.addWidget(self.again)
        col.addWidget(_buttons(self, "Add"))

    def accept(self):
        try:
            self.services.library.add_card(self.pack_id, CardInput(
                self.front.text(), self.back.toPlainText(), self.chapter.currentData()))
        except ApplicationError as e:
            error(self, e)
            return
        if self.again.isChecked():
            self.front.clear()
            self.back.clear()
            self.front.setFocus()
            return
        super().accept()


class SettingsDialog(QDialog):
    def __init__(self, services: Services, updater=None, parent=None):
        super().__init__(parent)
        self.services = services
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        col = QVBoxLayout(self)
        col.setSpacing(14)

        col.addWidget(QLabel("APPEARANCE", objectName="tileCaption"))
        self.mode = Segmented(["System", "Light", "Dark"])
        self.mode.set_index(theme.MODES.index(theme.manager().mode))
        self.mode.changed.connect(lambda i: theme.manager().set_mode(theme.MODES[i]))
        col.addWidget(self.mode)

        col.addWidget(QLabel("STUDY", objectName="tileCaption"))
        self.per_day = QSpinBox(minimum=0, maximum=500, suffix=" new cards a day")
        self.per_day.setValue(services.study.new_per_day())
        col.addWidget(self.per_day)
        col.addWidget(label("Fewer new cards means fewer reviews later. Around 20 a day "
                            "gets through the Cybearly manual in about three weeks.",
                            "hint", wrap=True))

        col.addWidget(QLabel("UPDATES", objectName="tileCaption"))
        auto = QCheckBox("Check for updates automatically")
        auto.setChecked(services.updates.auto_check())
        auto.toggled.connect(services.updates.set_auto_check)
        check = button("Check now")
        check.setEnabled(updater is not None)
        if updater is not None:
            check.clicked.connect(lambda: updater.check_now())
        row = QHBoxLayout()
        row.addWidget(auto)
        row.addStretch()
        row.addWidget(check)
        col.addLayout(row)
        col.addWidget(label(f"You have version {services.updates.current_version}.", "hint"))

        col.addWidget(QLabel("SCHOOL", objectName="tileCaption"))
        brand = services.library.branding()
        self.school = QLineEdit(brand.school)
        self.place = QLineEdit(brand.place)
        self.logo = brand.logo
        form = QFormLayout()
        form.addRow("Name", self.school)
        form.addRow("Town", self.place)
        logo_row = QHBoxLayout()
        self.preview = QLabel()
        self._preview()
        pick = button("Choose logo…")
        pick.clicked.connect(self._pick_logo)
        reset = button("Use the school emblem")
        reset.clicked.connect(lambda: (setattr(self, "logo", None), self._preview()))
        logo_row.addWidget(self.preview)
        logo_row.addWidget(pick)
        logo_row.addWidget(reset)
        logo_row.addStretch()
        form.addRow("Logo", logo_row)
        col.addLayout(form)
        col.addWidget(_buttons(self))

    def _preview(self):
        self.preview.setPixmap(logo_tile(self.logo or str(SCHOOL_EMBLEM), str(SCHOOL_EMBLEM), 38,
                                         self.devicePixelRatioF()))

    def _pick_logo(self):
        path, _f = QFileDialog.getOpenFileName(self, "School logo", "",
                                               "Pictures (*.png *.jpg *.jpeg *.svg)")
        if path:
            self.logo = path
            self._preview()

    def accept(self):
        self.services.study.set_new_per_day(self.per_day.value())
        self.services.library.set_branding(BrandingInput(self.school.text(), self.place.text(),
                                                         self.logo))
        super().accept()


class AboutDialog(QDialog):
    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        col = QVBoxLayout(self)
        col.setSpacing(8)
        col.setContentsMargins(28, 24, 28, 20)
        icon = QLabel(alignment=Qt.AlignCenter)
        icon.setPixmap(QPixmap(str(APP_ICON)).scaled(72, 72, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation))
        col.addWidget(icon)
        col.addWidget(QLabel(APP_NAME, objectName="sheetTitle", alignment=Qt.AlignCenter))
        col.addWidget(label(f"Version {__version__}", "muted"), 0, Qt.AlignCenter)
        text = label("Base camp for CTF study: chapters, spaced-repetition flashcards, "
                     "multiple-choice drills and a searchable cheatsheet, for any competition.",
                     "muted", wrap=True)
        text.setAlignment(Qt.AlignCenter)
        col.addWidget(text)
        brand = services.library.branding()
        school = QLabel(alignment=Qt.AlignCenter)
        school.setPixmap(logo_tile(brand.logo or str(SCHOOL_EMBLEM), str(SCHOOL_EMBLEM), 56,
                                   self.devicePixelRatioF()))
        col.addSpacing(8)
        col.addWidget(school)
        col.addWidget(QLabel(f"{brand.school}\n{brand.place}", objectName="school",
                             alignment=Qt.AlignCenter))
        col.addWidget(label("Study material belongs to its authors; packs made from it are "
                            "for your own study only — please don't share them.", "hint",
                            wrap=True))
        link = QLabel(f"<a href='{HOMEPAGE}'>{HOMEPAGE.removeprefix('https://')}</a>",
                      alignment=Qt.AlignCenter, openExternalLinks=True)
        col.addWidget(link)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        col.addWidget(close, 0, Qt.AlignCenter)
