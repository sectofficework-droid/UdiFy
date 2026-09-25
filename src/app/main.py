"""UdiFy PySide6 desktop application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.app.app_context import AppContext
from src.app.main_window import MainWindow
from src.app.theme import DARK, LIGHT, build_stylesheet
from src.config.settings import Environment
from src.diagnostics.logging_setup import configure_logging


def main() -> int:
    ctx = AppContext()
    configure_logging(ctx.settings.diagnostics_dir, ctx.settings.log_level)

    app = QApplication(sys.argv)
    palette = DARK if _system_prefers_dark(app) else LIGHT
    app.setStyleSheet(build_stylesheet(palette))

    window = MainWindow(ctx)
    window.show()

    exit_code = app.exec()
    ctx.close()
    return exit_code


def _system_prefers_dark(app: QApplication) -> bool:
    hints = app.styleHints()
    try:
        from PySide6.QtCore import Qt

        return hints.colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
