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
from . import i18n, theme, uiscale
from .background import restart_app
from .fit import scrollable
from .common import Segmented, button, error, label, logo_tile
from .i18n import _
from .icons import APP_ICON, SCHOOL_EMBLEM


def _buttons(dialog: QDialog, ok_text: str | None = None) -> QDialogButtonBox:
    box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    ok = box.button(QDialogButtonBox.Ok)
    ok.setText(ok_text or _("Save"))
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
        self.setWindowTitle(_("Edit pack") if pack else _("New study pack"))
        self.setMinimumWidth(480)
        col = QVBoxLayout(self)
        col.setSpacing(12)
        self.name = QLineEdit(objectName="titleEdit", placeholderText=_("Pack name, e.g. OliCyber 2027"))
        self.event = QLineEdit(placeholderText=_("Competition, e.g. Cybearly 2027 finals"))
        self.subtitle = QLineEdit(placeholderText=_("Optional note"))
        self.has_date = QCheckBox(_("Competition day"))
        self.date = QDateEdit(calendarPopup=True, displayFormat="d MMM yyyy")
        self.date.setDate(QDate.currentDate().addDays(30))
        self.has_date.toggled.connect(self.date.setEnabled)
        date_row = QHBoxLayout()
        date_row.addWidget(self.date)
        for text, days in ((_("In 2 weeks"), 14), (_("In a month"), 30), (_("In 3 months"), 91)):
            quick = button(text)
            quick.clicked.connect(lambda _c=False, d=days: (
                self.has_date.setChecked(True),
                self.date.setDate(QDate.currentDate().addDays(d))))
            date_row.addWidget(quick)
        date_row.addStretch()
        col.addWidget(self.name)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow(_("Competition"), self.event)
        form.addRow(self.has_date, date_row)
        form.addRow(_("Note"), self.subtitle)
        col.addLayout(form)
        col.addWidget(label(_("With a date set, the countdown shows on the home page and the "
                            "flashcard schedule makes sure every card comes back before the day."),
                            "hint", wrap=True))
        col.addWidget(_buttons(self, _("Save") if pack else _("Create")))
        scrollable(self)
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
        self.setWindowTitle(_("New card"))
        self.setMinimumWidth(520)
        col = QVBoxLayout(self)
        col.setSpacing(10)
        self.front = QLineEdit(objectName="titleEdit",
                               placeholderText=_("Question or term, e.g. What does nmap -sS do?"))
        self.back = QPlainTextEdit(placeholderText=_("Answer"))
        self.back.setFixedHeight(120)
        self.chapter = QComboBox()
        self.chapter.addItem(_("No chapter"), "")
        for c in services.study.chapters(pack_id):
            self.chapter.addItem(f"{c.id} · {c.title}", c.id)
        self.chapter.setCurrentIndex(max(0, self.chapter.findData(chapter_id)))
        self.again = QCheckBox(_("Add another after this one"))
        col.addWidget(self.front)
        col.addWidget(self.back)
        row = QHBoxLayout()
        row.addWidget(label(_("Chapter"), "muted"))
        row.addWidget(self.chapter, 1)
        col.addLayout(row)
        col.addWidget(self.again)
        col.addWidget(_buttons(self, _("Add")))
        scrollable(self)

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
        self.setWindowTitle(_("Settings"))
        self.setMinimumWidth(500)
        col = QVBoxLayout(self)
        col.setSpacing(14)

        col.addWidget(QLabel(_("APPEARANCE"), objectName="tileCaption"))
        self.mode = Segmented([_("System"), _("Light"), _("Dark")])
        self.mode.set_index(theme.MODES.index(theme.manager().mode))
        self.mode.changed.connect(lambda i: theme.manager().set_mode(theme.MODES[i]))
        col.addWidget(self.mode)

        col.addWidget(QLabel(_("STUDY"), objectName="tileCaption"))
        self.per_day = QSpinBox(minimum=0, maximum=500, suffix=" " + _("new cards a day"))
        self.per_day.setValue(services.study.new_per_day())
        col.addWidget(self.per_day)
        col.addWidget(label(_("Fewer new cards means fewer reviews later. Around 20 a day "
                            "gets through the Cybearly manual in about three weeks."),
                            "hint", wrap=True))

        col.addWidget(QLabel(_("INTERFACE SIZE"), objectName="tileCaption"))
        self.scale = QComboBox()
        for choice in uiscale.CHOICES:
            self.scale.addItem(_("Automatic") if choice == "auto" else f"{choice}%", choice)
        self.scale.setCurrentIndex(max(0, self.scale.findData(uiscale.chosen())))
        self.scale.currentIndexChanged.connect(self._scale_changed)
        col.addWidget(self.scale)
        col.addWidget(label(_("Applies after a restart. Automatic makes everything a little "
                            "smaller on small screens."), "hint", wrap=True))

        col.addWidget(QLabel(_("LANGUAGE"), objectName="tileCaption"))
        self.language = QComboBox()
        for code, name in i18n.LANGUAGES:
            self.language.addItem(_(name) if code == "" else name, code)
        self.language.setCurrentIndex(max(0, self.language.findData(i18n.chosen_language())))
        self.language.currentIndexChanged.connect(self._language_changed)
        col.addWidget(self.language)

        self.restart = button(_("Restart Bivouac now"))
        self.restart.hide()
        self.restart.clicked.connect(self._restart)
        col.addWidget(self.restart)

        col.addWidget(QLabel(_("UPDATES"), objectName="tileCaption"))
        auto = QCheckBox(_("Check for updates automatically"))
        auto.setChecked(services.updates.auto_check())
        auto.toggled.connect(services.updates.set_auto_check)
        check = button(_("Check now"))
        check.setEnabled(updater is not None)
        if updater is not None:
            check.clicked.connect(lambda: updater.check_now())
        row = QHBoxLayout()
        row.addWidget(auto)
        row.addStretch()
        row.addWidget(check)
        col.addLayout(row)
        col.addWidget(label(_("You have version {version}.").format(version=services.updates.current_version), "hint"))

        col.addWidget(QLabel(_("SCHOOL"), objectName="tileCaption"))
        brand = services.library.branding()
        self.school = QLineEdit(brand.school)
        self.place = QLineEdit(brand.place)
        self.logo = brand.logo
        form = QFormLayout()
        form.addRow(_("Name"), self.school)
        form.addRow(_("Town"), self.place)
        logo_row = QHBoxLayout()
        self.preview = QLabel()
        self._preview()
        pick = button(_("Choose logo…"))
        pick.clicked.connect(self._pick_logo)
        reset = button(_("Use the school emblem"))
        reset.clicked.connect(lambda: (setattr(self, "logo", None), self._preview()))
        logo_row.addWidget(self.preview)
        logo_row.addWidget(pick)
        logo_row.addWidget(reset)
        logo_row.addStretch()
        form.addRow(_("Logo"), logo_row)
        col.addLayout(form)
        col.addWidget(_buttons(self))
        scrollable(self)

    def _scale_changed(self):
        uiscale.set_chosen(self.scale.currentData())
        self.restart.show()

    def _language_changed(self):
        i18n.set_chosen_language(self.language.currentData())
        self.restart.show()

    def _restart(self):
        self.accept()
        restart_app()

    def _preview(self):
        self.preview.setPixmap(logo_tile(self.logo or str(SCHOOL_EMBLEM), str(SCHOOL_EMBLEM), 38,
                                         self.devicePixelRatioF()))

    def _pick_logo(self):
        path, _f = QFileDialog.getOpenFileName(self, _("School logo"), "",
                                               _("Pictures") + " (*.png *.jpg *.jpeg *.svg)")
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
        self.setWindowTitle(_("About {app}").format(app=APP_NAME))
        col = QVBoxLayout(self)
        col.setSpacing(8)
        col.setContentsMargins(28, 24, 28, 20)
        icon = QLabel(alignment=Qt.AlignCenter)
        icon.setPixmap(QPixmap(str(APP_ICON)).scaled(72, 72, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation))
        col.addWidget(icon)
        col.addWidget(QLabel(APP_NAME, objectName="sheetTitle", alignment=Qt.AlignCenter))
        col.addWidget(label(_("Version {version}").format(version=__version__), "muted"), 0, Qt.AlignCenter)
        text = label(_("Base camp for CTF study: chapters, spaced-repetition flashcards, "
                     "multiple-choice drills and a searchable cheatsheet, for any competition."),
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
        col.addWidget(label(_("Study material belongs to its authors; packs made from it are "
                            "for your own study only — please don't share them."), "hint",
                            wrap=True))
        link = QLabel(f"<a href='{HOMEPAGE}'>{HOMEPAGE.removeprefix('https://')}</a>",
                      alignment=Qt.AlignCenter, openExternalLinks=True)
        col.addWidget(link)
        close = QPushButton(_("Close"))
        close.clicked.connect(self.accept)
        col.addWidget(close, 0, Qt.AlignCenter)
