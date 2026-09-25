"""GUI smoke test: the PySide6 app constructs and tears down cleanly.

Not a full UI test (no click simulation) — just proves AppContext, the
demo MOCK dataset, MainWindow, and all nine screens wire together without
raising. Needs a real or virtual display, same runtime requirement as the
Playwright-driven integration tests need a Chromium binary.
"""

from __future__ import annotations

import pytest


def test_app_launches_and_closes(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")

    monkeypatch.setenv("UDIFY_SQLITE_PATH", str(tmp_path / "smoke.sqlite3"))
    monkeypatch.setenv("UDIFY_DIAGNOSTICS_DIR", str(tmp_path / "diagnostics"))
    monkeypatch.setenv("UDIFY_ENVIRONMENT", "MOCK")

    from PySide6.QtWidgets import QApplication

    from src.app.app_context import AppContext
    from src.app.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    ctx = AppContext()
    try:
        window = MainWindow(ctx)
        assert window.stack.count() == 8
        for key in window.screens:
            window._select_nav(key)
        assert len(ctx.demo_students) == 5
    finally:
        ctx.close()
