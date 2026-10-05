"""Chapters: the list on the left, a read-only study sheet on the right."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ...application.services import Services
from .. import theme
from ..common import (
    Card, Page, bullets_html, button, chip, clear, empty_state, label, primary_button, scroll,
)
from ..i18n import _

ID_ROLE = Qt.UserRole + 1


class QuestionBox(QWidget):
    """A self-check question whose answer stays hidden until asked for."""

    def __init__(self, number: int, question: str, answer: str, parent=None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 4, 0, 8)
        col.setSpacing(6)
        q = label(f"{number}. {question}", "bullet", wrap=True)
        q.setStyleSheet("font-weight: 600;")
        self.answer = label(answer, "muted", wrap=True)
        self.answer.hide()
        self.toggle = QPushButton(_("Show answer"), objectName="segment")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.clicked.connect(self._flip)
        row = QHBoxLayout()
        row.addWidget(self.toggle)
        row.addStretch()
        col.addWidget(q)
        col.addLayout(row)
        col.addWidget(self.answer)

    def _flip(self):
        shown = not self.answer.isVisible()
        self.answer.setVisible(shown)
        self.toggle.setText(_("Hide answer") if shown else _("Show answer"))


class ChaptersView(Page):
    practiseRequested = Signal(str)  # chapter id
    openPage = Signal(int)  # 0-based page of the source PDF

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id: str | None = None
        self.has_source = False
        self.title.setText(_("Chapters"))

        self.list = QListWidget()
        self.list.setMinimumWidth(270)
        self.list.currentItemChanged.connect(lambda item, _prev: self._show(item))

        self.sheet = QWidget()
        self.sheet_layout = QVBoxLayout(self.sheet)
        self.sheet_layout.setContentsMargins(0, 0, 8, 0)
        self.sheet_layout.setSpacing(14)

        left = Card(padding=8)
        left.add(self.list)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(scroll(self.sheet))
        split.setStretchFactor(1, 1)
        split.setSizes([300, 800])
        self.root.addWidget(split, 1)
        QShortcut(QKeySequence("R"), self, activated=self._toggle_read,
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence("P"), self, activated=self._practise,
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence("O"), self, activated=self._open_manual,
                  context=Qt.WidgetWithChildrenShortcut)

    # ---- data ---------------------------------------------------------------------
    def set_pack(self, pack_id: str | None):
        self.pack_id = pack_id
        self.refresh()

    def refresh(self, keep: str | None = None):
        keep = keep or self.current_id() or QSettings().value(f"chapter/{self.pack_id}")
        self.list.blockSignals(True)
        self.list.clear()
        chapters = self.services.study.chapters(self.pack_id) if self.pack_id else []
        pack = self.services.library.active() if self.pack_id else None
        self.has_source = bool(pack and pack.has_source)
        self.subtitle.setText(_("{read} of {total} read").format(
            read=sum(c.read for c in chapters), total=len(chapters)) if chapters else "")
        part = None
        select = None
        for c in chapters:
            if c.part and c.part != part:
                part = c.part
                header = QListWidgetItem(part.upper())
                header.setFlags(Qt.NoItemFlags)
                header.setForeground(theme.current_color("faint"))
                font = header.font()
                font.setPointSizeF(font.pointSizeF() * 0.8)
                font.setBold(True)
                header.setFont(font)
                self.list.addItem(header)
            item = QListWidgetItem(f"{'✓' if c.read else '   '}  {c.id}   {c.title}")
            item.setData(ID_ROLE, c.id)
            item.setToolTip(_("{known}/{cards} cards known").format(known=c.known, cards=c.cards))
            self.list.addItem(item)
            if c.id == keep or select is None:
                select = item
        self.list.blockSignals(False)
        if select is not None:
            self.list.setCurrentItem(select)
        self._show(self.list.currentItem())

    def current_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(ID_ROLE) if item else None

    def select(self, chapter_id: str):
        for i in range(self.list.count()):
            if self.list.item(i).data(ID_ROLE) == chapter_id:
                self.list.setCurrentRow(i)
                return

    # ---- the sheet ------------------------------------------------------------------
    def _show(self, item):
        clear(self.sheet_layout)
        if item is None or not item.data(ID_ROLE) or not self.pack_id:
            self.sheet_layout.addWidget(empty_state(
                _("No chapters"), _("This pack has no chapters. Packs made from a manual have one "
                                    "per chapter; your own packs can hold loose cards instead.")), 1)
            return
        c = self.services.study.chapter(self.pack_id, item.data(ID_ROLE))
        QSettings().setValue(f"chapter/{self.pack_id}", c.id)
        self.chapter = c

        head = QVBoxLayout()
        head.setSpacing(8)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        chips.addWidget(chip(_("Chapter {id}").format(id=c.id), "chipAccent"))
        if c.part:
            chips.addWidget(chip(c.part))
        chips.addWidget(chip(_("{known}/{cards} cards known").format(known=c.known, cards=c.cards), "chipGood" if c.cards and
                             c.known == c.cards else "chip"))
        if c.read:
            chips.addWidget(chip("✓ " + _("Read"), "chipGood"))
        chips.addStretch()
        head.addLayout(chips)
        title = QLabel(c.title, objectName="sheetTitle", wordWrap=True)
        head.addWidget(title)
        if c.blurb:
            head.addWidget(label(c.blurb, "muted", wrap=True))
        actions = QHBoxLayout()
        actions.setSpacing(8)
        practise = primary_button(_("Practise this chapter"), "cards")
        practise.setToolTip("P")
        practise.clicked.connect(self._practise)
        practise.setEnabled(c.cards > 0)
        actions.addWidget(practise)
        if self.has_source and c.page is not None:
            read = button(_("Open in manual"), "book")
            read.setToolTip(_("Page {number}").format(number=c.page + 1) + "  (O)")
            read.clicked.connect(self._open_manual)
            actions.addWidget(read)
        mark = button(_("Mark as unread") if c.read else _("Mark as read"), "check")
        mark.setToolTip("R")
        mark.clicked.connect(self._toggle_read)
        actions.addWidget(mark)
        actions.addStretch()
        head.addLayout(actions)
        self.sheet_layout.addLayout(head)

        if c.summary:
            recap = Card(_("What you should take away"))
            text = label("", "bullet", wrap=True)
            text.setTextFormat(Qt.RichText)
            text.setText(bullets_html(c.summary))
            recap.add(text)
            self.sheet_layout.addWidget(recap)

        if c.concepts:
            concepts = Card(_("Key concepts"))
            headers = list(c.concept_headers) or [_("Term"), _("Meaning"), _("Example")]
            columns = 3 if any(k.example for k in c.concepts) else 2
            headers = (headers + [_("Term"), _("Meaning"), _("Example")][len(headers):])[:columns]
            table = QTableWidget(len(c.concepts), columns, objectName="concepts")
            table.setHorizontalHeaderLabels(headers)
            table.verticalHeader().hide()
            table.setShowGrid(False)
            table.setWordWrap(True)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.NoSelection)
            table.setFocusPolicy(Qt.NoFocus)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            h = table.horizontalHeader()
            h.setDefaultAlignment(Qt.AlignLeft)
            h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            for col in range(1, columns):
                h.setSectionResizeMode(col, QHeaderView.Stretch)
            for row, k in enumerate(c.concepts):
                cells = (k.term, k.meaning, k.example)[:columns]
                for col, text in enumerate(cells):
                    cell = QTableWidgetItem(text)
                    if col == 0:
                        font = cell.font()
                        font.setBold(True)
                        cell.setFont(font)
                    table.setItem(row, col, cell)
            h.setMaximumSectionSize(260)
            table.resizeRowsToContents()
            concepts.add(table)
            self._fit_table(table)
            self.sheet_layout.addWidget(concepts)

        if c.quiz:
            quiz = Card(_("Check yourself"))
            quiz.add(label(_("Answer in your head (or out loud) before you peek."), "hint"))
            for n, q in enumerate(c.quiz, start=1):
                quiz.add(QuestionBox(n, q.question, q.answer))
            self.sheet_layout.addWidget(quiz)

        if c.sections:
            sections = Card(_("In the manual"))
            for s in c.sections:
                row = QPushButton(s.title + (f"   · p. {s.page + 1}" if s.page is not None else ""),
                                  objectName="icon")
                row.setStyleSheet("text-align: left; padding: 6px 8px;")
                row.setCursor(Qt.PointingHandCursor if self.has_source else Qt.ArrowCursor)
                row.setEnabled(self.has_source and s.page is not None)
                if s.page is not None:
                    row.clicked.connect(lambda _c=False, p=s.page: self.openPage.emit(p))
                sections.add(row)
            if not self.has_source:
                sections.add(label(_("Attach the original PDF (More → Attach original PDF…) "
                                     "to jump straight to these pages."), "hint", wrap=True))
            self.sheet_layout.addWidget(sections)

        if c.resources:
            res = Card(_("To go further"))
            text = label("", "muted", wrap=True)
            text.setTextFormat(Qt.RichText)
            text.setText(bullets_html(c.resources))
            res.add(text)
            self.sheet_layout.addWidget(res)
        self.sheet_layout.addStretch()

    def _fit_table(self, table: QTableWidget):
        def fit():
            table.resizeRowsToContents()
            height = table.horizontalHeader().height() + sum(
                table.rowHeight(r) for r in range(table.rowCount())) + 4
            table.setFixedHeight(height)
        table.horizontalHeader().sectionResized.connect(lambda *_args: fit())
        fit()

    # ---- actions ------------------------------------------------------------------
    def _toggle_read(self):
        cid = self.current_id()
        if cid and self.pack_id:
            self.services.study.set_read(self.pack_id, cid, not self.chapter.read)
            self.refresh(keep=cid)

    def _practise(self):
        if self.current_id():
            self.practiseRequested.emit(self.current_id())

    def _open_manual(self):
        if self.has_source and self.current_id() and self.chapter.page is not None:
            self.openPage.emit(self.chapter.page)
