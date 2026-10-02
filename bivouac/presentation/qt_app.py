"""Starts the Qt event loop around an already-wired set of services."""
from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .. import APP_ID, APP_NAME
from ..application.services import Services
from . import theme, uiscale
from .icons import APP_ICON


def create_application(argv: list[str]) -> QApplication:
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName(APP_NAME)
    QApplication.setDesktopFileName(APP_ID)
    if QApplication.instance() is None:
        uiscale.apply_before_app()  # Qt reads the scale factor once, as the app is created
    app = QApplication.instance() or QApplication(argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(APP_ICON)))
    theme.install(app)
    return app


def run(services: Services, argv: list[str]) -> int:
    from .main_window import MainWindow

    app = create_application(argv)
    window = MainWindow(services)
    window.show()
    return app.exec()
