"""Reference pages: the glossary, the command cheatsheet and the manual itself."""
from __future__ import annotations

import html

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPlainTextEdit, QSpinBox, QTextBrowser, QVBoxLayout, QWidget,
)

from ...application.services import Services
from .. import icons, theme
from ..common import Card, Page, clear, empty_state, icon_button, label, scroll


def search_box(placeholder: str) -> QLineEdit:
    box = QLineEdit(objectName="search", placeholderText=placeholder, clearButtonEnabled=True)
    box.setMinimumWidth(300)
    action = box.addAction(icons.icon("search", theme.current().faint), QLineEdit.LeadingPosition)
    theme.themed(lambda t: action.setIcon(icons.icon("search", t.faint)))
    return box


class GlossaryView(Page):
    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = None
        self.title.setText("Glossary")
        self.search = search_box("Search terms and definitions  (Ctrl+F)")
        self.search.textChanged.connect(lambda _t: self._timer.start())
        self.add_actions(self.search)
        QShortcut(QKeySequence.Find, self, activated=self.search.setFocus,
                  context=Qt.WidgetWithChildrenShortcut)
        self._timer = QTimer(self, singleShot=True, interval=120, timeout=self.refresh)
        card = Card(padding=6)
        self.view = QTextBrowser(objectName="bare")
        self.view.setOpenLinks(False)
        card.add(self.view)
        self.root.addWidget(card, 1)
        theme.themed(lambda _t: self.refresh())

    def set_pack(self, pack_id):
        self.pack_id = pack_id
        self.refresh()

    def refresh(self):
        if not self.pack_id:
            self.view.setHtml("")
            return
        terms = self.services.study.glossary(self.pack_id, self.search.text())
        total = len(self.services.study.glossary(self.pack_id))
        self.subtitle.setText(f"{len(terms)} of {total} terms" if self.search.text() else
                              f"{total} terms")
        t = theme.current()
        parts, letter = [], None
        for term in terms:
            first = term.term[:1].upper()
            if first != letter:
                letter = first
                parts.append(f"<h3 style='color:{t.accent}; margin:14px 0 4px 0'>"
                             f"{html.escape(letter)}</h3>")
            parts.append(f"<p style='margin:0 0 10px 0'><b>{html.escape(term.term)}</b>"
                         f"<br><span style='color:{t.muted}'>{html.escape(term.definition)}"
                         f"</span></p>")
        if not terms:
            parts.append(f"<p style='color:{t.faint}'>" + (
                "Nothing matches. Try fewer words." if total else
                "This pack has no glossary.") + "</p>")
        self.view.setHtml(f"<div style='color:{t.text}'>{''.join(parts)}</div>")


class CodeBlock(QPlainTextEdit):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("code")
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lines = text.count("\n") + 1
        self.setFixedHeight(QFontMetrics(self.document().defaultFont()).lineSpacing() * lines + 22)


class CheatsheetView(Page):
    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = None
        self.title.setText("Cheatsheet")
        self.search = search_box("Search commands, tools, flags  (Ctrl+F)")
        self.search.textChanged.connect(lambda _t: self._timer.start())
        self.add_actions(self.search)
        QShortcut(QKeySequence.Find, self, activated=self.search.setFocus,
                  context=Qt.WidgetWithChildrenShortcut)
        self._timer = QTimer(self, singleShot=True, interval=150, timeout=self.refresh)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 8, 0)
        self.body_layout.setSpacing(12)
        self.root.addWidget(scroll(self.body), 1)

    def set_pack(self, pack_id):
        self.pack_id = pack_id
        self.refresh()

    def refresh(self):
        clear(self.body_layout)
        groups = self.services.study.cheatsheet(self.pack_id, self.search.text()) \
            if self.pack_id else []
        self.subtitle.setText(f"{len(groups)} groups · for labs and CTFs you're allowed to "
                              "attack only")
        if not groups:
            self.body_layout.addWidget(empty_state(
                "Nothing here", "Nothing matches your search." if self.search.text() else
                "This pack has no cheatsheet."), 1)
            return
        section = None
        for g in groups:
            if g.section != section:
                section = g.section
                self.body_layout.addWidget(label(section.upper(), "partHeader"))
            card = Card(g.title)
            text = "\n".join(g.lines)
            copy = icon_button("copy", "Copy all")
            copy.clicked.connect(lambda _c=False, t=text: QGuiApplication.clipboard().setText(t))
            card.title_row.addWidget(copy)
            card.add(CodeBlock(text))
            self.body_layout.addWidget(card)
        self.body_layout.addStretch()


class ManualView(Page):
    """The pack's original PDF, opened at the page a chapter or section points to."""

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = None
        self.path = None
        self.title.setText("Manual")
        self.doc = QPdfDocument(self)
        self.view = QPdfView()
        self.view.setDocument(self.doc)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.setKeyboardTracking(False)
        self.page.valueChanged.connect(lambda n: self.go(n - 1))
        self.view.pageNavigator().currentPageChanged.connect(self._sync_page)
        zoom_out = icon_button("zoom-out", "Zoom out (Ctrl+-)")
        zoom_in = icon_button("zoom-in", "Zoom in (Ctrl+=)")
        fit = icon_button("fit-day", "Fit width (Ctrl+0)")
        zoom_out.clicked.connect(lambda: self._zoom(1 / 1.2))
        zoom_in.clicked.connect(lambda: self._zoom(1.2))
        fit.clicked.connect(lambda: self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth))
        self.of = label("", "muted")
        self.add_actions(label("Page", "muted"), self.page, self.of, zoom_out, fit, zoom_in)
        for keys, slot in (("Ctrl+=", lambda: self._zoom(1.2)), ("Ctrl++", lambda: self._zoom(1.2)),
                           ("Ctrl+-", lambda: self._zoom(1 / 1.2)),
                           ("Ctrl+0", fit.click)):
            QShortcut(QKeySequence(keys), self, activated=slot,
                      context=Qt.WidgetWithChildrenShortcut)
        card = Card(padding=0)
        card.add(self.view)
        self.root.addWidget(card, 1)
        self.missing = empty_state("No manual attached",
                                   "Import a manual PDF, or attach one to this pack from "
                                   "More → Attach original PDF…")
        self.root.addWidget(self.missing, 1)
        self.card = card

    def set_pack(self, pack_id):
        self.pack_id = pack_id
        path = self.services.library.source_path(pack_id) if pack_id else None
        if path != self.path:
            self.doc.close()
            self.path = path
            if path:
                self.doc.load(path)
        has = bool(path) and self.doc.pageCount() > 0
        self.card.setVisible(has)
        self.missing.setVisible(not has)
        self.page.setMaximum(max(1, self.doc.pageCount()))
        self.of.setText(f"of {self.doc.pageCount()}")
        pack = self.services.library.active()
        self.subtitle.setText(pack.title if pack and has else "")

    def go(self, page: int):
        if 0 <= page < self.doc.pageCount():
            self.view.pageNavigator().jump(page, QPointF(0, 0), self.view.zoomFactor())

    def _sync_page(self, page: int):
        self.page.blockSignals(True)
        self.page.setValue(page + 1)
        self.page.blockSignals(False)

    def _zoom(self, factor: float):
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(max(0.3, min(4.0, self.view.zoomFactor() * factor)))
