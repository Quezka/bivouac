"""The window, driven headlessly: every page builds, study flows work from the keyboard."""
import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from bivouac.presentation.qt_app import create_application
    app = create_application([])
    app.setOrganizationName("BivouacTests")  # keep the user's window settings out of it
    return app


@pytest.fixture
def window(app, services):
    from PySide6.QtCore import QSettings
    QSettings().clear()
    from bivouac.presentation.main_window import MainWindow
    w = MainWindow(services)
    w.show()
    w.activateWindow()
    pump()
    yield w
    w.close()


def pump(ms=30):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def test_empty_shelf_shows_the_welcome(window):
    assert window.pack_id is None
    assert window.overview.title.text() == "Welcome to Bivouac"
    assert not window.nav_buttons[window.PRACTICE].isEnabled()


def test_every_page_builds_with_a_pack(window, services, pack):
    window.load_pack()
    for i in range(window.MANUAL):
        window.show_page(i)
        pump()
        assert window.stack.currentIndex() == i
    assert not window.nav_buttons[window.MANUAL].isVisible()  # no PDF attached
    window.show_page(window.MANUAL)
    assert window.stack.currentIndex() == 0


def test_flashcards_from_the_keyboard(window, services, pack):
    window.load_pack()
    window.show_page(window.PRACTICE)
    flash = window.practice.flash
    first = flash.queue[0]
    QTest.keyClick(flash, Qt.Key_Space)
    assert flash.revealed and flash.back.isVisibleTo(flash)
    QTest.keyClick(flash, Qt.Key_3)
    assert flash.done == 1 and flash.queue[0].id != first.id
    assert services.study.overview(pack.id).seen == 1
    QTest.keyClick(flash, Qt.Key_Space)
    QTest.keyClick(flash, Qt.Key_1)  # again: stays in the session
    assert flash.done == 1 and any(c.id for c in flash.queue)


def test_multiple_choice_marks_right_and_wrong(window, pack):
    window.load_pack()
    window.show_page(window.PRACTICE)
    window.practice.mode.set_index(1)
    window.practice.restart()
    choice = window.practice.choice
    q = choice.question
    choice.pick(q.answer)
    assert choice.buttons[q.answer].objectName() == "optionRight"
    assert choice.right == 1
    QTest.keyClick(choice, Qt.Key_Space)
    assert not choice.answered


def test_chapter_sheet_and_practise_button(window, pack):
    window.load_pack()
    window.open_chapter("1")
    assert window.chapters.current_id() == "1"
    window.chapters._toggle_read()
    assert window.chapters.chapter.read
    window.chapters._practise()
    assert window.stack.currentIndex() == window.PRACTICE
    assert window.practice.scope.currentData() == "ch:1"


def test_theme_modes_rebuild(window, pack):
    from bivouac.presentation import theme
    window.load_pack()
    for mode in ("dark", "light", "system"):
        theme.manager().set_mode(mode)
        pump()


def test_digest_lists_chapters_and_filters(window, pack):
    window.load_pack()
    window.show_page(window.DIGEST)
    digest = window.digest
    assert digest.subtitle.text() == "5 key terms in 2 chapters"
    digest.search.setText("injection")
    digest.refresh()
    assert digest.subtitle.text() == "1 of 2 chapters match · 1 key terms"
    digest.search.setText("zzz")
    digest.refresh()
    digest.search.setText("")
    digest.show_what.set_index(2)
    digest.show_what.changed.emit(2)
    pump()


def test_digest_opens_a_chapter(window, pack):
    window.load_pack()
    window.digest.chapterRequested.emit("2")
    assert window.stack.currentIndex() == window.CHAPTERS
    assert window.chapters.current_id() == "2"
