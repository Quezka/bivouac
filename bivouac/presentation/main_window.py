from __future__ import annotations

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu,
    QMessageBox, QSizePolicy, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..application.errors import ApplicationError
from ..application.services import Services
from ..application.types import SCOPE_CHAPTER
from .fit import clamp_window
from . import theme
from .common import confirm, error, logo_tile
from .dialogs import AboutDialog, CardDialog, PackDialog, SettingsDialog
from .i18n import N_, _, plural
from .icons import APP_ICON, SCHOOL_EMBLEM
from .views.chapters import ChaptersView
from .views.digest import DigestView
from .views.overview import OverviewView
from .views.practice import PracticeView
from .updates_ui import UpdateChecker
from .views.reference import CheatsheetView, GlossaryView, ManualView


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(232)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        brand_icon = QLabel()
        brand_icon.setPixmap(QIcon(str(APP_ICON)).pixmap(28, 28))
        brand = QHBoxLayout()
        brand.setContentsMargins(12, 4, 12, 0)
        brand.setSpacing(10)
        brand.addWidget(brand_icon)
        brand.addWidget(QLabel(APP_NAME, objectName="brand"))
        brand.addStretch()

        self.pack_button = QToolButton(objectName="packButton")
        self.pack_button.setPopupMode(QToolButton.InstantPopup)
        self.pack_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.pack_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pack_button.setCursor(Qt.PointingHandCursor)
        theme.set_icon(self.pack_button, "flag", "flag", size=16)
        self.pack_button.setToolTip(_("Switch study pack"))

        self.nav = QVBoxLayout()
        self.nav.setSpacing(2)
        self.footer = QVBoxLayout()
        self.footer.setSpacing(2)

        self.school_logo = QLabel()
        self.school_name = QLabel(objectName="school", wordWrap=True)
        self.school_place = QLabel(objectName="place")
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(self.school_name)
        names.addWidget(self.school_place)
        school = QHBoxLayout()
        school.setContentsMargins(10, 0, 6, 6)
        school.setSpacing(10)
        school.addWidget(self.school_logo, 0, Qt.AlignVCenter)
        school.addLayout(names, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 14)
        layout.setSpacing(6)
        layout.addLayout(brand)
        layout.addSpacing(12)
        layout.addWidget(self.pack_button)
        layout.addSpacing(10)
        layout.addLayout(self.nav)
        layout.addStretch()
        layout.addLayout(school)
        layout.addLayout(self.footer)

    def nav_button(self, icon_name: str, text: str, checkable: bool = True) -> QToolButton:
        button = QToolButton(objectName="nav", text=f"  {text}", checkable=checkable)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setIconSize(QSize(18, 18))
        button.setCursor(Qt.PointingHandCursor)
        theme.set_icon(button, icon_name, "muted", "accent" if checkable else None)
        return button

    def add_page(self, icon_name: str, text: str, shortcut: str) -> QToolButton:
        button = self.nav_button(icon_name, text)
        button.setToolTip(f"{text}  ({shortcut})")
        self.group.addButton(button, len(self.group.buttons()))
        self.nav.addWidget(button)
        return button

    def set_branding(self, brand):
        self.school_logo.setPixmap(logo_tile(brand.logo or str(SCHOOL_EMBLEM), str(SCHOOL_EMBLEM),
                                             38, self.devicePixelRatioF()))
        self.school_name.setText(brand.school)
        self.school_place.setText(brand.place)


class MainWindow(QMainWindow):
    PAGES = [("home", N_("Overview")), ("book", N_("Chapters")), ("list", N_("Digest")),
             ("cards", N_("Practice")), ("file-text", N_("Glossary")),
             ("terminal", N_("Cheatsheet")), ("layers", N_("Manual"))]
    CHAPTERS, DIGEST, PRACTICE, MANUAL = 1, 2, 3, 6

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.pack_id: str | None = None
        self.setWindowTitle(APP_NAME)
        clamp_window(self, 1240, 820, 980, 640)

        self.overview = OverviewView(services)
        self.chapters = ChaptersView(services)
        self.digest = DigestView(services)
        self.practice = PracticeView(services)
        self.glossary = GlossaryView(services)
        self.cheatsheet = CheatsheetView(services)
        self.manual = ManualView(services)
        self.pages = [self.overview, self.chapters, self.digest, self.practice, self.glossary,
                      self.cheatsheet, self.manual]

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self.nav_buttons = []
        for i, (page, (icon_name, text)) in enumerate(zip(self.pages, self.PAGES)):
            self.stack.addWidget(page)
            self.nav_buttons.append(self.sidebar.add_page(icon_name, _(text), f"Ctrl+{i + 1}"))
            self._shortcut(f"Ctrl+{i + 1}", lambda i=i: self.show_page(i))
        self.sidebar.group.idClicked.connect(self.show_page)
        self.sidebar.set_branding(services.library.branding())
        self.updater = UpdateChecker(services, self)  # not `update`: that's QWidget's

        more = self.sidebar.nav_button("more", _("More"), checkable=False)
        more.setPopupMode(QToolButton.InstantPopup)
        more.setMenu(self._more_menu())
        self.sidebar.footer.addWidget(more)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.overview.studyRequested.connect(lambda: self.show_page(self.PRACTICE))
        self.overview.chapterRequested.connect(self.open_chapter)
        self.overview.importRequested.connect(self.import_file)
        self.overview.newPackRequested.connect(self.new_pack)
        self.overview.editPackRequested.connect(self.edit_pack)
        self.chapters.practiseRequested.connect(self.practise_chapter)
        self.chapters.openPage.connect(self.open_manual)
        self.digest.chapterRequested.connect(self.open_chapter)
        self.digest.openPage.connect(self.open_manual)
        self.practice.addCardRequested.connect(self.add_card)
        self.practice.changed.connect(self._dirty_counts)

        settings = QSettings()
        geometry = settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.load_pack()
        self.show_page(int(settings.value("window/tab", 0)))

    # ---- packs --------------------------------------------------------------------
    def load_pack(self):
        pack = self.services.library.active()
        self.pack_id = pack.id if pack else None
        self.sidebar.pack_button.setText(f" {pack.title}" if pack else " " + _("No pack yet"))
        self.sidebar.pack_button.setMenu(self._pack_menu())
        for i in range(1, len(self.pages)):
            self.nav_buttons[i].setEnabled(pack is not None)
        self.nav_buttons[self.MANUAL].setVisible(bool(pack and pack.has_source))
        for page in self.pages:
            page.set_pack(self.pack_id)
        self.setWindowTitle(f"{pack.title} — {APP_NAME}" if pack else APP_NAME)
        for action in self.pack_actions:
            action.setEnabled(pack is not None)

    def _pack_menu(self) -> QMenu:
        menu = QMenu(self)
        for p in self.services.library.packs():
            action = menu.addAction(p.title, lambda pid=p.id: self.switch_pack(pid))
            action.setCheckable(True)
            action.setChecked(p.id == self.pack_id)
        if menu.actions():
            menu.addSeparator()
        menu.addAction(_("Import manual or pack…"), self.import_file)
        menu.addAction(_("New empty pack…"), self.new_pack)
        return menu

    def switch_pack(self, pack_id: str):
        self.services.library.set_active(pack_id)
        self.load_pack()

    def import_file(self):
        path, _f = QFileDialog.getOpenFileName(
            self, _("Import a manual or a study pack"), QSettings().value("import/dir", ""),
            ";;".join([_("Manuals and packs") + " (*.pdf *.json)",
                       _("Competition manual") + " (*.pdf)",
                       _("Study pack") + " (*.json)"]))
        if not path:
            return
        from pathlib import Path
        QSettings().setValue("import/dir", str(Path(path).parent))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            pack = self.services.library.import_file(path)
        except ApplicationError as e:
            QApplication.restoreOverrideCursor()
            error(self, e, _("Couldn't import that"))
            return
        QApplication.restoreOverrideCursor()
        self.load_pack()
        self.show_page(0)
        QMessageBox.information(
            self, _("Pack ready"),
            _("{title}: {chapters} and {cards}.").format(
                title=pack.title, chapters=plural(pack.chapter_count, "chapter"),
                cards=plural(pack.card_count, "card"))
            + "\n\n" + _("Set the competition date in More → Edit pack details to get a "
                          "countdown."))

    def new_pack(self):
        dialog = PackDialog(self.services, parent=self)
        if dialog.exec():
            self.load_pack()
            self.show_page(self.PRACTICE)

    def edit_pack(self):
        pack = self.services.library.active()
        if pack and PackDialog(self.services, pack, self).exec():
            self.load_pack()

    def attach_source(self):
        path, _f = QFileDialog.getOpenFileName(self, _("The pack's original PDF"), "",
                                               "PDF (*.pdf)")
        if path and self.pack_id:
            try:
                self.services.library.attach_source(self.pack_id, path)
            except ApplicationError as e:
                error(self, e)
            self.load_pack()

    def export_pack(self):
        if not self.pack_id:
            return
        path, _f = QFileDialog.getSaveFileName(self, _("Export study pack"),
                                               f"{self.pack_id}.json",
                                               _("Study pack") + " (*.json)")
        if path:
            try:
                self.services.library.export(self.pack_id, path)
            except ApplicationError as e:
                error(self, e)

    def delete_pack(self):
        pack = self.services.library.active()
        if pack and confirm(self, _("Delete pack"),
                            _("Delete “{title}”, your own cards in it and all its progress? "
                              "This can't be undone.").format(title=pack.title)):
            self.services.library.delete(pack.id)
            self.load_pack()

    def reset_progress(self):
        pack = self.services.library.active()
        if pack and confirm(self, _("Reset progress"),
                            _("Forget every answer and chapter read in “{title}”? "
                              "The cards themselves stay.").format(title=pack.title),
                            _("Reset")):
            self.services.study.reset_progress(pack.id)
            self.load_pack()

    def add_card(self, chapter_id: str = ""):
        if self.pack_id and CardDialog(self.services, self.pack_id, chapter_id, self).exec():
            self.practice.reload_scopes()
            self.practice.restart()

    # ---- navigation ---------------------------------------------------------------
    def show_page(self, index: int):
        if not 0 <= index < len(self.pages) or not self.nav_buttons[index].isEnabled() \
                or not self.nav_buttons[index].isVisible() and index == self.MANUAL:
            index = 0
        self.stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        if index == self.CHAPTERS:
            self.chapters.refresh()
        elif index == self.DIGEST:
            self.digest.refresh()
        elif index == self.PRACTICE:
            if self._counts_dirty:
                self.practice.reload_scopes()
                self._counts_dirty = False
            self.practice.focus_panel()

    _counts_dirty = False

    def _dirty_counts(self):
        self._counts_dirty = True

    def open_chapter(self, chapter_id: str):
        self.show_page(self.CHAPTERS)
        self.chapters.select(chapter_id)

    def practise_chapter(self, chapter_id: str):
        self.show_page(self.PRACTICE)
        self.practice.practise(SCOPE_CHAPTER + chapter_id)

    def open_manual(self, page: int):
        self.show_page(self.MANUAL)
        self.manual.go(page)

    def _shortcut(self, keys, slot):
        action = QAction(self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(slot)
        self.addAction(action)

    def _more_menu(self) -> QMenu:
        menu = QMenu(self)
        self.pack_actions = []
        entries = [
            (_("Import manual or pack…"), "Ctrl+O", self.import_file, False),
            (_("New empty pack…"), None, self.new_pack, False),
            (_("Edit pack details…"), "Ctrl+E", self.edit_pack, True),
            (_("Add a card…"), "Ctrl+Shift+N", lambda: self.add_card(""), True),
            (_("Attach original PDF…"), None, self.attach_source, True),
            (_("Export pack…"), None, self.export_pack, True),
            None,
            (_("Reset progress…"), None, self.reset_progress, True),
            (_("Delete pack…"), None, self.delete_pack, True),
            None,
            (_("Settings…"), "Ctrl+,", self.open_settings, False),
            (_("Check for updates…"), None, lambda: self.updater.check_now(), False),
            (_("Keyboard shortcuts"), None, self.show_shortcuts, False),
            (_("About {app}").format(app=APP_NAME), None,
             lambda: AboutDialog(self.services, self).exec(), False),
            None,
            (_("Quit {app}").format(app=APP_NAME), "Ctrl+Q", self.close, False),
        ]
        for entry in entries:
            if entry is None:
                menu.addSeparator()
                continue
            text, keys, slot, needs_pack = entry
            action = menu.addAction(text, slot)
            if keys:
                action.setShortcut(QKeySequence(keys))
                action.setShortcutVisibleInContextMenu(True)
                self.addAction(action)  # so the shortcut works with the menu closed
            if needs_pack:
                self.pack_actions.append(action)
        return menu

    def open_settings(self):
        if SettingsDialog(self.services, self.updater, self).exec():
            self.sidebar.set_branding(self.services.library.branding())
            self.load_pack()

    def show_shortcuts(self):
        QMessageBox.information(self, _("Keyboard shortcuts"), "\n".join([
            "Ctrl+1 … Ctrl+7\t" + _("Switch page"),
            "Ctrl+O\t" + _("Import a manual or pack"),
            "Ctrl+E\t" + _("Edit pack details"),
            "Ctrl+Shift+N\t" + _("Add a card"),
            "",
            _("Flashcards"),
            "Space\t" + _("Show answer, then Good"),
            "1 2 3 4\t" + _("Again · Hard · Good · Easy"),
            "",
            _("Multiple choice"),
            "1 2 3 4\t" + _("Pick an answer"),
            "Space\t" + _("Next question"),
            "",
            _("Chapters"),
            "R\t" + _("Mark as read / unread"),
            "P\t" + _("Practise the chapter"),
            "O\t" + _("Open it in the manual"),
            "",
            "Ctrl+F\t" + _("Search the glossary or cheatsheet"),
        ]))

    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/tab", self.stack.currentIndex())
        super().closeEvent(event)
