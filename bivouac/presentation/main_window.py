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
from . import theme
from .common import confirm, error, logo_tile
from .dialogs import AboutDialog, CardDialog, PackDialog, SettingsDialog
from .icons import APP_ICON, SCHOOL_EMBLEM
from .views.chapters import ChaptersView
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
        self.pack_button.setToolTip("Switch study pack")

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
    PAGES = [("home", "Overview"), ("book", "Chapters"), ("cards", "Practice"),
             ("file-text", "Glossary"), ("terminal", "Cheatsheet"), ("layers", "Manual")]

    def __init__(self, services: Services):
        super().__init__()
        self.services = services
        self.pack_id: str | None = None
        self.setWindowTitle(APP_NAME)
        self.resize(1240, 820)
        self.setMinimumSize(980, 640)

        self.overview = OverviewView(services)
        self.chapters = ChaptersView(services)
        self.practice = PracticeView(services)
        self.glossary = GlossaryView(services)
        self.cheatsheet = CheatsheetView(services)
        self.manual = ManualView(services)
        self.pages = [self.overview, self.chapters, self.practice, self.glossary,
                      self.cheatsheet, self.manual]

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self.nav_buttons = []
        for i, (page, (icon_name, text)) in enumerate(zip(self.pages, self.PAGES)):
            self.stack.addWidget(page)
            self.nav_buttons.append(self.sidebar.add_page(icon_name, text, f"Ctrl+{i + 1}"))
            self._shortcut(f"Ctrl+{i + 1}", lambda i=i: self.show_page(i))
        self.sidebar.group.idClicked.connect(self.show_page)
        self.sidebar.set_branding(services.library.branding())
        self.updater = UpdateChecker(services, self)  # not `update`: that's QWidget's

        more = self.sidebar.nav_button("more", "More", checkable=False)
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

        self.overview.studyRequested.connect(lambda: self.show_page(2))
        self.overview.chapterRequested.connect(self.open_chapter)
        self.overview.importRequested.connect(self.import_file)
        self.overview.newPackRequested.connect(self.new_pack)
        self.overview.editPackRequested.connect(self.edit_pack)
        self.chapters.practiseRequested.connect(self.practise_chapter)
        self.chapters.openPage.connect(self.open_manual)
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
        self.sidebar.pack_button.setText(f" {pack.title}" if pack else " No pack yet")
        self.sidebar.pack_button.setMenu(self._pack_menu())
        for i in range(1, len(self.pages)):
            self.nav_buttons[i].setEnabled(pack is not None)
        self.nav_buttons[5].setVisible(bool(pack and pack.has_source))
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
        menu.addAction("Import manual or pack…", self.import_file)
        menu.addAction("New empty pack…", self.new_pack)
        return menu

    def switch_pack(self, pack_id: str):
        self.services.library.set_active(pack_id)
        self.load_pack()

    def import_file(self):
        path, _f = QFileDialog.getOpenFileName(
            self, "Import a manual or a study pack", QSettings().value("import/dir", ""),
            "Manuals and packs (*.pdf *.json);;Competition manual (*.pdf);;Study pack (*.json)")
        if not path:
            return
        from pathlib import Path
        QSettings().setValue("import/dir", str(Path(path).parent))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            pack = self.services.library.import_file(path)
        except ApplicationError as e:
            QApplication.restoreOverrideCursor()
            error(self, e, "Couldn't import that")
            return
        QApplication.restoreOverrideCursor()
        self.load_pack()
        self.show_page(0)
        QMessageBox.information(
            self, "Pack ready", f"{pack.title}: {pack.chapter_count} chapters and "
                                f"{pack.card_count} cards.\n\nSet the competition date in "
                                "More → Edit pack details to get a countdown.")

    def new_pack(self):
        dialog = PackDialog(self.services, parent=self)
        if dialog.exec():
            self.load_pack()
            self.show_page(2)

    def edit_pack(self):
        pack = self.services.library.active()
        if pack and PackDialog(self.services, pack, self).exec():
            self.load_pack()

    def attach_source(self):
        path, _f = QFileDialog.getOpenFileName(self, "The pack's original PDF", "",
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
        path, _f = QFileDialog.getSaveFileName(self, "Export study pack",
                                               f"{self.pack_id}.json", "Study pack (*.json)")
        if path:
            try:
                self.services.library.export(self.pack_id, path)
            except ApplicationError as e:
                error(self, e)

    def delete_pack(self):
        pack = self.services.library.active()
        if pack and confirm(self, "Delete pack",
                            f"Delete “{pack.title}”, your own cards in it and all its progress? "
                            "This can't be undone."):
            self.services.library.delete(pack.id)
            self.load_pack()

    def reset_progress(self):
        pack = self.services.library.active()
        if pack and confirm(self, "Reset progress",
                            f"Forget every answer and chapter read in “{pack.title}”? "
                            "The cards themselves stay.", "Reset"):
            self.services.study.reset_progress(pack.id)
            self.load_pack()

    def add_card(self, chapter_id: str = ""):
        if self.pack_id and CardDialog(self.services, self.pack_id, chapter_id, self).exec():
            self.practice.reload_scopes()
            self.practice.restart()

    # ---- navigation ---------------------------------------------------------------
    def show_page(self, index: int):
        if not 0 <= index < len(self.pages) or not self.nav_buttons[index].isEnabled() \
                or not self.nav_buttons[index].isVisible() and index == 5:
            index = 0
        self.stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        if index == 1:
            self.chapters.refresh()
        elif index == 2:
            if self._counts_dirty:
                self.practice.reload_scopes()
                self._counts_dirty = False
            self.practice.focus_panel()

    _counts_dirty = False

    def _dirty_counts(self):
        self._counts_dirty = True

    def open_chapter(self, chapter_id: str):
        self.show_page(1)
        self.chapters.select(chapter_id)

    def practise_chapter(self, chapter_id: str):
        self.show_page(2)
        self.practice.practise(SCOPE_CHAPTER + chapter_id)

    def open_manual(self, page: int):
        self.show_page(5)
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
            ("Import manual or pack…", "Ctrl+O", self.import_file, False),
            ("New empty pack…", None, self.new_pack, False),
            ("Edit pack details…", "Ctrl+E", self.edit_pack, True),
            ("Add a card…", "Ctrl+Shift+N", lambda: self.add_card(""), True),
            ("Attach original PDF…", None, self.attach_source, True),
            ("Export pack…", None, self.export_pack, True),
            None,
            ("Reset progress…", None, self.reset_progress, True),
            ("Delete pack…", None, self.delete_pack, True),
            None,
            ("Settings…", "Ctrl+,", self.open_settings, False),
            ("Check for updates…", None, lambda: self.updater.check_now(), False),
            ("Keyboard shortcuts", None, self.show_shortcuts, False),
            (f"About {APP_NAME}", None, lambda: AboutDialog(self.services, self).exec(), False),
            None,
            (f"Quit {APP_NAME}", "Ctrl+Q", self.close, False),
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
        QMessageBox.information(self, "Keyboard shortcuts", "\n".join([
            "Ctrl+1 … Ctrl+6\tSwitch page",
            "Ctrl+O\tImport a manual or pack",
            "Ctrl+E\tEdit pack details",
            "Ctrl+Shift+N\tAdd a card",
            "",
            "Flashcards",
            "Space\tShow answer, then Good",
            "1 2 3 4\tAgain · Hard · Good · Easy",
            "",
            "Multiple choice",
            "1 2 3 4\tPick an answer",
            "Space\tNext question",
            "",
            "Chapters",
            "R\tMark as read / unread",
            "P\tPractise the chapter",
            "O\tOpen it in the manual",
            "",
            "Ctrl+F\tSearch the glossary or cheatsheet",
        ]))

    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/tab", self.stack.currentIndex())
        super().closeEvent(event)
