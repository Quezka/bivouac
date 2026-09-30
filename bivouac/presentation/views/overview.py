"""The home page: countdown to the competition, today's work, progress per chapter."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ...application.services import Services
from .. import theme
from ..common import (
    Card, HistoryChart, Page, StatTile, button, clear, empty_state, label, primary_button, scroll,
)
from ..formatting import fmt_date, short_day

PART_OF_DAY = ((12, "Good morning"), (18, "Good afternoon"), (24, "Good evening"))


class ChapterRow(QPushButton):
    """One chapter: number, title, how much of it is known, and whether it was read."""

    def __init__(self, chapter, parent=None):
        super().__init__(parent)
        self.setObjectName("icon")
        self.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(12)
        number = QLabel(chapter.id, objectName="chipAccent" if chapter.read else "chip")
        number.setFixedWidth(46)
        number.setAlignment(Qt.AlignCenter)
        title = QLabel(chapter.title)
        title.setAttribute(Qt.WA_TransparentForMouseEvents)
        bar = QProgressBar(textVisible=False, maximum=max(1, chapter.cards))
        bar.setValue(chapter.known)
        bar.setFixedWidth(140)
        if chapter.cards and chapter.known == chapter.cards:
            bar.setObjectName("done")
        count = label(f"{chapter.known}/{chapter.cards}", "hint")
        count.setFixedWidth(52)
        count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for w in (number, title):
            row.addWidget(w)
        row.addStretch()
        row.addWidget(bar)
        row.addWidget(count)
        self.setToolTip(f"{chapter.seen} of {chapter.cards} cards seen, {chapter.known} known"
                        + (" · read" if chapter.read else ""))
        self.setMinimumHeight(40)


class OverviewView(Page):
    studyRequested = Signal()
    chapterRequested = Signal(str)
    importRequested = Signal()
    newPackRequested = Signal()
    editPackRequested = Signal()

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id: str | None = None
        self.study = primary_button("Study now", "cards")
        self.study.setShortcut("Ctrl+Return")
        self.study.clicked.connect(self.studyRequested.emit)
        self.add_actions(self.study)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)
        self.root.addWidget(self.content, 1)

    def set_pack(self, pack_id: str | None):
        self.pack_id = pack_id
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        clear(self.content_layout)
        brand = self.services.library.branding()
        if self.pack_id is None:
            self.title.setText("Welcome to Bivouac")
            self.subtitle.setText(f"Base camp for CTF study · {brand.school}")
            self.study.hide()
            box = empty_state(
                "Pitch your first camp",
                "Import a competition manual (the Cybearly “Campo base” PDF works as is), "
                "open a pack a friend shared, or start an empty pack and write your own cards.")
            row = QHBoxLayout()
            row.addStretch()
            imp = primary_button("Import manual or pack…", "upload")
            imp.clicked.connect(self.importRequested.emit)
            new = button("Start an empty pack…", "plus")
            new.clicked.connect(self.newPackRequested.emit)
            row.addWidget(imp)
            row.addWidget(new)
            row.addStretch()
            box.layout().insertLayout(3, row)
            self.content_layout.addWidget(box, 1)
            return
        self.study.show()
        o = self.services.study.overview(self.pack_id)
        from datetime import datetime
        hour = datetime.now().hour
        greeting = next(text for limit, text in PART_OF_DAY if hour < limit)
        self.title.setText(o.pack.title)
        self.subtitle.setText(f"{greeting} · {brand.school}, {brand.place}")
        t = theme.current()

        tiles = QGridLayout()
        tiles.setSpacing(12)
        countdown = StatTile("Competition")
        if o.days_left is None:
            countdown.show_value("—", "No date yet. Set it in Edit pack to see a countdown "
                                      "and keep cards timed for the day.")
            link = button("Set the date…")
            link.clicked.connect(self.editPackRequested.emit)
            countdown.add(link)
        elif o.days_left > 0:
            countdown.value.setObjectName("countdown")
            countdown.show_value(f"{o.days_left} day{'s' if o.days_left != 1 else ''}",
                                 f"to {o.pack.event or o.pack.title}, {fmt_date(o.pack.event_date)}")
        elif o.days_left == 0:
            countdown.show_value("Today!", f"{o.pack.event or o.pack.title} — in bocca al lupo!",
                                 t.flag)
        else:
            countdown.show_value("Done", f"{o.pack.event or 'The competition'} was "
                                         f"{fmt_date(o.pack.event_date)}")
        work = StatTile("Today")
        todo = o.due + o.new
        work.show_value(str(todo) if todo else "✓",
                        f"{o.due} to review, {o.new} new" if todo else
                        f"All caught up · {o.reviewed_today} answers today",
                        None if todo else t.success)
        known = StatTile("Known")
        pct = round(100 * o.known / o.total) if o.total else 0
        known.show_value(f"{pct}%", f"{o.known} of {o.total} cards solid, {o.seen} seen")
        bar = QProgressBar(textVisible=False, maximum=max(1, o.total))
        bar.setValue(o.known)
        known.add(bar)
        streak = StatTile("Streak")
        streak.show_value(f"{o.streak} day{'s' if o.streak != 1 else ''}",
                          f"{o.chapters_read} of {len(o.chapters)} chapters read")
        for i, tile in enumerate((countdown, work, known, streak)):
            tiles.addWidget(tile, 0, i)
            tiles.setColumnStretch(i, 1)
        self.content_layout.addLayout(tiles)

        lower = QHBoxLayout()
        lower.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(16)
        history = Card("Last two weeks")
        chart = HistoryChart()
        chart.set_values([(short_day(d), n) for d, n in o.history])
        history.add(chart)
        history.add(label(f"{sum(n for _d, n in o.history)} answers in 14 days", "hint"))
        left.addWidget(history)
        tips = Card("How to use it")
        tips.add(label("1. Read a chapter in the manual (Chapters → Open in manual).\n"
                       "2. Go through its recap and self-check questions.\n"
                       "3. Do your flashcards every day — a little, often.\n"
                       "4. Before the day, drill multiple choice and skim the cheatsheet.",
                       "muted", wrap=True))
        left.addWidget(tips)
        left.addStretch()
        lower.addLayout(left, 2)

        chapters = Card("Chapters")
        rows = QWidget()
        col = QVBoxLayout(rows)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        for chapter in o.chapters:
            row = ChapterRow(chapter)
            row.clicked.connect(lambda _c=False, cid=chapter.id: self.chapterRequested.emit(cid))
            col.addWidget(row)
        if not o.chapters:
            col.addWidget(label("This pack has no chapters — its cards are all loose. "
                                "Add cards from the Practice page.", "hint", wrap=True))
        col.addStretch()
        chapters.add(scroll(rows), 1)
        lower.addWidget(chapters, 3)
        self.content_layout.addLayout(lower, 1)
