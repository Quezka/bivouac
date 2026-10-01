"""Digest: every chapter boiled down to its takeaways and key terms, to skim from start to end."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ...application.services import Services
from .. import theme
from ..common import Card, Page, Segmented, bullets_html, button, chip, clear, empty_state, \
    label, scroll
from .reference import search_box

EVERYTHING, TAKEAWAYS, TERMS = range(3)


def terms_html(concepts) -> str:
    t = theme.current()
    rows = "".join(
        f"<tr><td style='padding:3px 16px 3px 0; white-space:nowrap' valign='top'>"
        f"<b>{html.escape(k.term)}</b></td>"
        f"<td style='padding:3px 0; color:{t.muted}'>{html.escape(k.meaning)}"
        + (f" <i style='color:{t.faint}'>— {html.escape(k.example)}</i>" if k.example else "")
        + "</td></tr>" for k in concepts)
    return f"<table cellspacing='0'>{rows}</table>"


class DigestView(Page):
    chapterRequested = Signal(str)
    openPage = Signal(int)  # 0-based page of the source PDF

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id: str | None = None
        self.has_source = False
        self.title.setText("Digest")
        self.show_what = Segmented(["Everything", "Takeaways", "Key terms"])
        self.show_what.changed.connect(lambda _i: self.refresh())
        self.search = search_box("Search the whole manual  (Ctrl+F)")
        self.search.textChanged.connect(lambda _t: self._timer.start())
        self.add_actions(self.show_what, self.search)
        QShortcut(QKeySequence.Find, self, activated=self.search.setFocus,
                  context=Qt.WidgetWithChildrenShortcut)
        self._timer = QTimer(self, singleShot=True, interval=150, timeout=self.refresh)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 8, 0)
        self.body_layout.setSpacing(12)
        self.root.addWidget(scroll(self.body), 1)
        theme.themed(lambda _t: self.refresh())

    def set_pack(self, pack_id: str | None):
        self.pack_id = pack_id
        pack = self.services.library.active() if pack_id else None
        self.has_source = bool(pack and pack.has_source)
        self.refresh()

    def refresh(self):
        clear(self.body_layout)
        digest = self.services.study.digest(self.pack_id, self.search.text()) \
            if self.pack_id else None
        if digest is None or not digest.total_chapters:
            self.subtitle.setText("")
            self.body_layout.addWidget(empty_state(
                "Nothing to skim", "This pack has no chapter recaps or key terms yet. "
                                   "Packs made from a manual get one per chapter."), 1)
            return
        shown = sum(len(c.concepts) for c in digest.chapters)
        self.subtitle.setText(
            f"{digest.total_concepts} key terms in {digest.total_chapters} chapters"
            if not self.search.text() else
            f"{len(digest.chapters)} of {digest.total_chapters} chapters match · "
            f"{shown} key terms")
        if not digest.chapters:
            self.body_layout.addWidget(empty_state("Nothing matches", "Try fewer words."), 1)
            return
        mode, part = self.show_what.index(), None
        for c in digest.chapters:
            if c.part and c.part != part:
                part = c.part
                self.body_layout.addWidget(label(part.upper(), "partHeader"))
            self.body_layout.addWidget(self._chapter_card(c, mode))
        self.body_layout.addStretch()

    def _chapter_card(self, c, mode: int) -> Card:
        card = Card(f"{c.id}   {c.title}")
        if c.read:
            card.title_row.insertWidget(1, chip("✓ Read", "chipGood"))
        if self.has_source and c.page is not None:
            page = QPushButton(f"p. {c.page + 1}", objectName="icon")
            page.setToolTip("Open the manual at this chapter")
            page.setCursor(Qt.PointingHandCursor)
            page.clicked.connect(lambda _c=False, p=c.page: self.openPage.emit(p))
            card.title_row.addWidget(page)
        more = button("Chapter")
        more.setToolTip("Open the chapter: self-check questions, sections, practice")
        more.clicked.connect(lambda _c=False, cid=c.id: self.chapterRequested.emit(cid))
        card.title_row.addWidget(more)
        if c.takeaways and mode != TERMS:
            text = label("", "bullet", wrap=True)
            text.setTextFormat(Qt.RichText)
            text.setText(bullets_html(c.takeaways))
            card.add(text)
        if c.concepts and mode != TAKEAWAYS:
            terms = label("", "bullet", wrap=True)
            terms.setTextFormat(Qt.RichText)
            terms.setText(terms_html(c.concepts))
            card.add(terms)
        return card
