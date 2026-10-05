"""Practice: spaced-repetition flashcards and a multiple-choice drill."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from ...application.errors import ApplicationError
from ...application.services import Services
from ...application.types import SCOPE_ALL, SCOPE_CHAPTER, CardKind, Grade
from ..common import (
    Card, Page, Segmented, button, chip, clear, empty_state, error, label, primary_button,
)
from ..i18n import N_, _, plural

KIND_LABEL = {CardKind.CONCEPT: N_("Key concept"), CardKind.TERM: N_("Glossary"),
              CardKind.QUESTION: N_("Self-check"), CardKind.CUSTOM: N_("My card")}
GRADES = ((Grade.AGAIN, N_("Again"), "1", "gradeAgain",
           N_("Didn't know it: see it again in a moment")),
          (Grade.HARD, N_("Hard"), "2", "grade", N_("Got it, with effort")),
          (Grade.GOOD, N_("Good"), "3", "grade", N_("Knew it")),
          (Grade.EASY, N_("Easy"), "4", "grade", N_("Too easy: show it much later")))


class FlashcardPanel(QWidget):
    """One card at a time: the prompt, then (Space) the answer and four grades."""

    changed = Signal()

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id: str | None = None
        self.queue = []
        self.done = 0
        self.revealed = False
        self.cram = False
        self.scope = SCOPE_ALL
        self.setFocusPolicy(Qt.StrongFocus)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        top = QHBoxLayout()
        self.progress_label = label("", "muted")
        self.bar = QProgressBar(textVisible=False)
        self.bar.setFixedWidth(220)
        top.addWidget(self.progress_label)
        top.addStretch()
        top.addWidget(self.bar)
        col.addLayout(top)

        self.card = Card(padding=28)
        self.card.setMinimumHeight(340)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        self.card.body.addLayout(self.chips)
        self.card.body.addStretch()
        self.front = QLabel(objectName="flashFront", wordWrap=True, alignment=Qt.AlignCenter)
        self.front.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.back = QLabel(objectName="flashBack", wordWrap=True, alignment=Qt.AlignCenter)
        self.back.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.detail = QLabel(objectName="flashDetail", wordWrap=True, alignment=Qt.AlignCenter)
        self.card.add(self.front)
        self.card.add(self.back)
        self.card.add(self.detail)
        self.card.body.addStretch()

        self.reveal = primary_button(_("Show answer"), None)
        self.reveal.setToolTip("Space")
        self.reveal.setFocusPolicy(Qt.NoFocus)
        self.reveal.clicked.connect(self.show_answer)
        self.grades = QWidget()
        grades = QHBoxLayout(self.grades)
        grades.setContentsMargins(0, 0, 0, 0)
        grades.setSpacing(8)
        grades.addStretch()
        for grade, text, key, role, tip in GRADES:
            b = QPushButton(f"{_(text)}  ({key})", objectName=role)
            b.setToolTip(_(tip))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _c=False, g=grade: self.answer(g))
            grades.addWidget(b)
        grades.addStretch()
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.reveal)
        actions.addStretch()
        self.card.body.addLayout(actions)
        self.card.add(self.grades)
        col.addWidget(self.card, 1)

        self.finished = QWidget()
        fcol = QVBoxLayout(self.finished)
        fcol.setContentsMargins(0, 0, 0, 0)
        self.finished_box = QVBoxLayout()
        fcol.addLayout(self.finished_box)
        col.addWidget(self.finished, 1)

        for key, slot in (("Space", self._space), ("Return", self._space),
                          ("1", lambda: self._grade_key(Grade.AGAIN)),
                          ("2", lambda: self._grade_key(Grade.HARD)),
                          ("3", lambda: self._grade_key(Grade.GOOD)),
                          ("4", lambda: self._grade_key(Grade.EASY))):
            QShortcut(QKeySequence(key), self, activated=slot, context=Qt.WidgetWithChildrenShortcut)

    def start(self, pack_id: str | None, scope: str, cram: bool):
        self.pack_id, self.scope, self.cram = pack_id, scope, cram
        self.queue = self.services.study.queue(pack_id, scope, cram) if pack_id else []
        self.done = 0
        self._show()

    def _show(self):
        total = self.done + len(self.queue)
        self.bar.setMaximum(max(1, total))
        self.bar.setValue(self.done)
        self.progress_label.setText(_("{left} left · {done} done").format(
            left=len(self.queue), done=self.done)
            + (" · " + _("cram (ignores the schedule)") if self.cram else ""))
        if not self.queue:
            self.card.hide()
            self.finished.show()
            clear(self.finished_box)
            if self.done:
                title, hint = _("Nice work!"), (
                    _("You went through {cards}. Come back tomorrow: the schedule brings each "
                      "card back just before you'd forget it.").format(
                          cards=plural(self.done, "card")))
            else:
                title, hint = _("All caught up"), _("Nothing is due here right now. You can "
                                                    "cram anyway, or drill multiple choice.")
            box = empty_state(title, hint)
            if not self.cram and self.pack_id:
                row = QHBoxLayout()
                row.addStretch()
                again = button(_("Cram this set anyway"), "shuffle")
                again.clicked.connect(lambda: self.start(self.pack_id, self.scope, True))
                row.addWidget(again)
                row.addStretch()
                box.layout().insertLayout(3, row)
            self.finished_box.addWidget(box)
            return
        self.finished.hide()
        self.card.show()
        card = self.queue[0]
        clear(self.chips)
        self.chips.addStretch()
        self.chips.addWidget(chip(_(KIND_LABEL[card.kind]), "chipAccent"))
        if card.chapter_title:
            self.chips.addWidget(chip(f"{card.chapter_id} · {card.chapter_title}"))
        if card.new:
            self.chips.addWidget(chip(_("New"), "chipGood"))
        self.chips.addStretch()
        self.front.setObjectName("flashQuestion" if len(card.front) > 60 else "flashFront")
        self.front.style().unpolish(self.front)  # the object name picks the style
        self.front.style().polish(self.front)
        self.front.setText(card.front)
        self.back.setText(card.back)
        self.detail.setText(_("e.g. {example}").format(example=card.detail) if card.detail else "")
        self.revealed = False
        self.back.hide()
        self.detail.hide()
        self.grades.hide()
        self.reveal.show()

    def show_answer(self):
        if not self.queue:
            return
        self.revealed = True
        self.back.show()
        self.detail.setVisible(bool(self.detail.text()))
        self.reveal.hide()
        self.grades.show()

    def answer(self, grade: Grade):
        if not self.queue or not self.revealed:
            return
        card = self.queue.pop(0)
        try:
            self.services.study.grade(self.pack_id, card.id, grade)
        except ApplicationError as e:
            error(self, e)
        if grade is Grade.AGAIN:  # see it again later in this session
            self.queue.insert(min(len(self.queue), 4), card)
        else:
            self.done += 1
        self.changed.emit()
        self._show()

    def _space(self):
        if self.queue and not self.revealed:
            self.show_answer()
        elif self.queue:
            self.answer(Grade.GOOD)

    def _grade_key(self, grade: Grade):
        if self.revealed:
            self.answer(grade)


class ChoicePanel(QWidget):
    """"Which term matches?": four options, keys 1–4, then Space for the next one."""

    changed = Signal()

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = None
        self.scope = SCOPE_ALL
        self.question = None
        self.answered = False
        self.right = self.total = 0
        self.setFocusPolicy(Qt.StrongFocus)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        top = QHBoxLayout()
        self.score = label("", "muted")
        top.addWidget(self.score)
        top.addStretch()
        col.addLayout(top)
        self.card = Card(padding=28)
        self.chips = QHBoxLayout()
        self.card.body.addLayout(self.chips)
        self.card.add(label(_("Which term matches?"), "hint"))
        self.prompt = QLabel(objectName="flashQuestion", wordWrap=True)
        self.prompt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.card.add(self.prompt)
        self.options_box = QVBoxLayout()
        self.options_box.setSpacing(8)
        self.card.body.addLayout(self.options_box)
        self.feedback = label("", "muted", wrap=True)
        self.card.add(self.feedback)
        row = QHBoxLayout()
        row.addStretch()
        self.next = primary_button(_("Next"), "chevron-right")
        self.next.setToolTip("Space")
        self.next.setFocusPolicy(Qt.NoFocus)
        self.next.clicked.connect(self.ask)
        row.addWidget(self.next)
        self.card.body.addLayout(row)
        self.card.body.addStretch()
        col.addWidget(self.card, 1)
        self.empty = empty_state(_("Nothing to drill"), _("This set has no terms or concepts to "
                                                       "build questions from."))
        col.addWidget(self.empty, 1)
        for i in range(4):
            QShortcut(QKeySequence(str(i + 1)), self, activated=lambda i=i: self.pick(i),
                      context=Qt.WidgetWithChildrenShortcut)
        for key in ("Space", "Return"):
            QShortcut(QKeySequence(key), self, activated=self._space,
                      context=Qt.WidgetWithChildrenShortcut)

    def start(self, pack_id, scope):
        self.pack_id, self.scope = pack_id, scope
        self.right = self.total = 0
        self.ask()

    def ask(self):
        self.question = self.services.study.choice(self.pack_id, self.scope) \
            if self.pack_id else None
        self.card.setVisible(self.question is not None)
        self.empty.setVisible(self.question is None)
        self.score.setText(_("{right} of {total} right this round").format(
            right=self.right, total=self.total) if self.total else
            _("Pick the term the definition describes"))
        if self.question is None:
            return
        q = self.question
        clear(self.chips)
        self.chips.addWidget(chip(q.chapter_title))
        self.chips.addStretch()
        self.prompt.setText(q.prompt)
        clear(self.options_box)
        self.buttons = []
        for i, option in enumerate(q.options):
            b = QPushButton(f"{i + 1}.  {option}", objectName="option")
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _c=False, i=i: self.pick(i))
            self.options_box.addWidget(b)
            self.buttons.append(b)
        self.feedback.setText("")
        self.next.hide()
        self.answered = False

    def pick(self, i: int):
        if self.question is None or self.answered or i >= len(self.question.options):
            return
        self.answered = True
        q = self.question
        correct = i == q.answer
        self.total += 1
        self.right += correct
        for n, b in enumerate(self.buttons):
            b.setObjectName("optionRight" if n == q.answer else
                            "optionWrong" if n == i else "option")
            b.style().unpolish(b)
            b.style().polish(b)
        self.feedback.setText(_("Right!") if correct else
                              _("It's “{answer}”. The card will come back in your "
                                "flashcards soon.").format(answer=q.options[q.answer]))
        try:
            self.services.study.answer_choice(self.pack_id, q.card_id, correct)
        except ApplicationError as e:
            error(self, e)
        self.score.setText(_("{right} of {total} right this round").format(
            right=self.right, total=self.total))
        self.next.show()
        self.setFocus()
        self.changed.emit()

    def _space(self):
        if self.answered:
            self.ask()


class PracticeView(Page):
    addCardRequested = Signal(str)  # chapter id, or ""
    changed = Signal()

    def __init__(self, services: Services, parent=None):
        super().__init__(parent)
        self.services = services
        self.pack_id = None
        self.title.setText(_("Practice"))
        self.subtitle.setText(_("Flashcards come back just before you'd forget them"))
        self.mode = Segmented([_("Flashcards"), _("Multiple choice")])
        self.mode.changed.connect(lambda _i: self.restart())
        for b in self.mode.group.buttons():
            b.setFocusPolicy(Qt.NoFocus)
        self.scope = QComboBox()
        self.scope.setMinimumWidth(260)
        self.scope.setMaximumWidth(380)
        self.scope.activated.connect(lambda _i: self.restart())
        self.scope.setFocusPolicy(Qt.ClickFocus)
        self.cram = QCheckBox(_("Cram"))
        self.cram.setToolTip(_("Go through the whole set now, weakest cards first, "
                               "whatever the schedule says"))
        self.cram.toggled.connect(lambda _on: self.restart())
        self.cram.setFocusPolicy(Qt.NoFocus)
        add = button(_("Add card"), "plus")
        add.setToolTip(_("Write a card of your own (Ctrl+Shift+N)"))
        add.setShortcut("Ctrl+Shift+N")
        add.clicked.connect(lambda: self.addCardRequested.emit(
            self.scope.currentData().removeprefix(SCOPE_CHAPTER)
            if (self.scope.currentData() or "").startswith(SCOPE_CHAPTER) else ""))
        self.add_actions(self.mode, self.scope, self.cram, add)

        self.stack = QStackedWidget()
        self.flash = FlashcardPanel(services)
        self.choice = ChoicePanel(services)
        self.flash.changed.connect(self.changed.emit)
        self.choice.changed.connect(self.changed.emit)
        self.stack.addWidget(self.flash)
        self.stack.addWidget(self.choice)
        self.root.addWidget(self.stack, 1)

    def set_pack(self, pack_id):
        self.pack_id = pack_id
        self.reload_scopes()
        self.restart()

    def reload_scopes(self, select: str | None = None):
        select = select or self.scope.currentData() or \
            QSettings().value(f"scope/{self.pack_id}", SCOPE_ALL)
        self.scope.blockSignals(True)
        self.scope.clear()
        for s in self.services.study.scopes(self.pack_id) if self.pack_id else []:
            due = "  · " + _("{due} due").format(due=s.due) if s.due else ""
            self.scope.addItem(f"{_(s.label)}  ({s.cards}){due}", s.key)
        i = self.scope.findData(select)
        self.scope.setCurrentIndex(max(0, i))
        self.scope.blockSignals(False)

    def focus_panel(self):
        self.stack.currentWidget().setFocus()

    def practise(self, scope: str):
        self.reload_scopes(scope)
        self.restart()

    def restart(self):
        key = self.scope.currentData() or SCOPE_ALL
        if self.pack_id:
            QSettings().setValue(f"scope/{self.pack_id}", key)
        self.cram.setEnabled(self.mode.index() == 0)
        self.stack.setCurrentIndex(self.mode.index())
        if self.mode.index() == 0:
            self.flash.start(self.pack_id, key, self.cram.isChecked())
        else:
            self.choice.start(self.pack_id, key)
        self.focus_panel()
