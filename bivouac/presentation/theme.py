"""Bivouac's look is the suite's theme (quezka_ui.theme) in the school's blue and red, plus the rules only
Bivouac's pages need (flash cards, quiz options, progress bars, the pack button...). This module sets that
brand and then stands in for the shared one, so the app's imports keep working."""
import sys

from quezka_ui import theme as _shared


def _css(t) -> str:
    return f"""
    QToolButton#packButton {{ background: {t.surface}; border: 1px solid {t.border};
        border-radius: 9px; padding: 7px 10px; text-align: left; color: {t.text};
        font-weight: 600; }}
    QToolButton#packButton:hover {{ border-color: {t.accent}; }}
    #countdown {{ font-size: 30pt; font-weight: 800; color: {t.flag}; }}
    QLabel#chipAccent {{ background: {t.accent_soft}; color: {t.accent};
        border-radius: 10px; padding: 3px 10px; font-size: 9pt; font-weight: 600; }}
    QLabel#chipGood {{ background: {t.raised}; color: {t.success};
        border-radius: 10px; padding: 3px 10px; font-size: 9pt; font-weight: 600; }}
    #flashFront {{ font-size: 20pt; font-weight: 700; color: {t.text}; }}
    #flashQuestion {{ font-size: 14pt; font-weight: 600; color: {t.text}; }}
    #flashBack {{ font-size: 12.5pt; color: {t.text}; }}
    #flashDetail {{ color: {t.muted}; font-style: italic; }}
    #partHeader {{ color: {t.faint}; font-size: 8.5pt; font-weight: 600; letter-spacing: 1px; }}
    #bullet {{ color: {t.text}; }}
    QPushButton#option {{ background: {t.surface}; border: 1px solid {t.border};
        border-radius: 10px; padding: 12px 16px; text-align: left; font-size: 11pt; }}
    QPushButton#option:hover {{ border-color: {t.accent}; background: {t.surface}; }}
    QPushButton#optionRight {{ background: {t.surface}; border: 2px solid {t.success};
        border-radius: 10px; padding: 11px 15px; text-align: left; font-size: 11pt;
        color: {t.success}; font-weight: 600; }}
    QPushButton#optionWrong {{ background: {t.surface}; border: 2px solid {t.danger};
        border-radius: 10px; padding: 11px 15px; text-align: left; font-size: 11pt;
        color: {t.danger}; }}
    QPushButton#grade {{ padding: 8px 14px; font-weight: 600; }}
    QPushButton#gradeAgain {{ padding: 8px 14px; font-weight: 600; color: {t.danger}; }}
    QPlainTextEdit#code {{ background: {t.raised}; border: none; border-radius: 8px;
        font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
        font-size: 9.5pt; padding: 6px 8px; }}
    QProgressBar {{ background: {t.raised}; border: none; border-radius: 3px; max-height: 6px;
        min-height: 6px; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}
    QProgressBar#done::chunk {{ background: {t.success}; }}
    QTableWidget#concepts {{ background: transparent; }}
    QTableWidget#concepts::item {{ padding: 6px 8px; border-bottom: 1px solid {t.border}; }}
    """


_shared.school_brand(css=_css)
sys.modules[__name__] = _shared
