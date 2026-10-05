"""Building blocks shared by the pages: header, cards, buttons, chips, segmented control."""
from __future__ import annotations

import html

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from . import theme
from .i18n import _


class Page(QWidget):
    """A top-level page: padded, themed background, header row on top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(28, 22, 28, 24)
        self.root.setSpacing(18)
        self.title = QLabel(objectName="pageTitle")
        self.subtitle = QLabel(objectName="pageSubtitle")
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        self.header.addLayout(titles)
        self.header.addStretch()
        self.root.addLayout(self.header)

    def add_actions(self, *widgets):
        for w in widgets:
            self.header.addWidget(w, 0, Qt.AlignVCenter)


class Card(QFrame):
    """Rounded surface with an optional title row."""

    def __init__(self, title: str | None = None, padding: int = 16, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(padding, padding, padding, padding)
        self.body.setSpacing(10)
        self.title_row = QHBoxLayout()
        self.title_row.setSpacing(8)
        if title:
            self.title_label = QLabel(title, objectName="cardTitle")
            self.title_row.addWidget(self.title_label)
            self.title_row.addStretch()
            self.body.addLayout(self.title_row)

    def add(self, widget, stretch: int = 0):
        self.body.addWidget(widget, stretch)
        return widget


class StatTile(Card):
    def __init__(self, caption: str):
        super().__init__(padding=16)
        self.body.setSpacing(4)
        self.caption = QLabel(caption.upper(), objectName="tileCaption")
        self.value = QLabel(objectName="tileValue")
        self.detail = label()
        self.detail.setWordWrap(True)
        for widget in (self.caption, self.value, self.detail):
            self.add(widget)
        self.body.addStretch()

    def show_value(self, value: str, detail: str = "", color: str | None = None):
        self.value.setText(value)
        self.value.setStyleSheet(f"color: {color};" if color else "")
        self.detail.setText(detail)


class Segmented(QFrame):
    """A row of mutually exclusive choices, in place of tabs."""

    changed = Signal(int)

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.group = QButtonGroup(self)
        for i, text in enumerate(labels):
            b = QPushButton(text, objectName="segment", checkable=True)
            b.setCursor(Qt.PointingHandCursor)
            bold = QFont(b.font())
            bold.setBold(True)  # the checked segment is bold: leave room for it
            b.setMinimumWidth(QFontMetrics(bold).horizontalAdvance(text) + 30)
            self.group.addButton(b, i)
            row.addWidget(b)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.changed.emit)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def index(self) -> int:
        return self.group.checkedId()

    def set_index(self, i: int):
        self.group.button(i).setChecked(True)


class HistoryChart(QWidget):
    """Answers per day as small rounded bars; today is the last, in the accent colour."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values: list[tuple[str, int]] = []
        self.setMinimumHeight(110)

    def set_values(self, values: list[tuple[str, int]]):
        self.values = values
        self.setToolTip("\n".join(f"{d}: {n}" for d, n in values))
        self.update()

    def paintEvent(self, _event):
        if not self.values:
            return
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        font = QFont(self.font())
        font.setPointSizeF(font.pointSizeF() * 0.8)
        p.setFont(font)
        top, bottom = 6, 18
        h = self.height() - top - bottom
        slot = self.width() / len(self.values)
        bar = min(22.0, slot * 0.62)
        peak = max(1, max(n for _d, n in self.values))
        for i, (day, n) in enumerate(self.values):
            x = i * slot + (slot - bar) / 2
            height = max(3.0, h * n / peak) if n else 3.0
            last = i == len(self.values) - 1
            color = QColor(t.accent if last else (t.faint if not n else t.accent))
            if not last and n:
                color.setAlphaF(0.45)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(x, top + h - height, bar, height), 3, 3)
            if i % 2 == len(self.values) % 2 or last:
                p.setPen(QColor(t.faint))
                p.drawText(QRectF(i * slot - 10, top + h + 2, slot + 20, bottom), Qt.AlignCenter,
                           day)
        p.end()


def label(text: str = "", role: str = "muted", wrap: bool = False) -> QLabel:
    result = QLabel(text, objectName=role)
    result.setWordWrap(wrap)
    if wrap:
        result.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return result


def chip(text: str, role: str = "chip") -> QLabel:
    result = QLabel(text, objectName=role)
    result.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return result


def primary_button(text: str, icon_name: str | None = "plus") -> QPushButton:
    result = QPushButton(text, objectName="primary")
    result.setCursor(Qt.PointingHandCursor)
    if icon_name:
        theme.set_icon(result, icon_name, "on_accent", size=16)
    return result


def button(text: str, icon_name: str | None = None) -> QPushButton:
    result = QPushButton(text)
    result.setCursor(Qt.PointingHandCursor)
    if icon_name:
        theme.set_icon(result, icon_name, "muted", size=16)
    return result


def icon_button(name: str, tooltip: str) -> QToolButton:
    result = QToolButton(objectName="icon", toolTip=tooltip)
    result.setCursor(Qt.PointingHandCursor)
    theme.set_icon(result, name, "muted")
    return result


def scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setWidget(widget)
    return area


def bullets_html(items) -> str:
    return "".join(f"<p style='margin:0 0 6px 0'>•&nbsp;&nbsp;{html.escape(i)}</p>"
                   for i in items)


def empty_state(title: str, hint: str) -> QWidget:
    box = QWidget()
    col = QVBoxLayout(box)
    col.addStretch()
    head = QLabel(title, objectName="sheetTitle", alignment=Qt.AlignCenter)
    body = label(hint, "muted", wrap=True)
    body.setAlignment(Qt.AlignCenter)
    col.addWidget(head)
    col.addWidget(body)
    col.addStretch()
    return box


def error_text(err: Exception) -> str:
    """An application error's message in the user's language."""
    template = getattr(err, "template", None)
    if template is None:
        return _(str(err))
    return _(template).format(**err.values) if err.values else _(template)


def error(parent, err: Exception, title: str | None = None):
    """`title` and the error's message (if it's one of the fixed ones) come out translated."""
    QMessageBox.warning(parent, title or _("Something went wrong"), error_text(err))


def confirm(parent, title: str, text: str, action: str | None = None) -> bool:
    box = QMessageBox(QMessageBox.Warning, title, text, parent=parent)
    ok = box.addButton(action or _("Delete"), QMessageBox.DestructiveRole)
    box.addButton(QMessageBox.Cancel)
    box.exec()
    return box.clickedButton() is ok


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


def logo_tile(path: str, fallback: str, size: int, ratio: float = 1.0) -> QPixmap:
    """A logo on a small white rounded tile, so dark logos show on the dark theme too."""
    logo = QPixmap(path)
    if logo.isNull():
        logo = QPixmap(fallback)
    px = int(size * ratio)
    tile = QPixmap(px, px)
    tile.fill(Qt.transparent)
    p = QPainter(tile)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(0, 0, px, px), px * 0.22, px * 0.22)
    pad = px * 0.1
    inner = logo.scaled(int(px - 2 * pad), int(px - 2 * pad), Qt.KeepAspectRatio,
                        Qt.SmoothTransformation)
    p.drawPixmap(int((px - inner.width()) / 2), int((px - inner.height()) / 2), inner)
    p.end()
    tile.setDevicePixelRatio(ratio)
    return tile
