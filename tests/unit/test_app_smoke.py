"""GUI smoke test: the PySide6 app constructs and tears down cleanly.

Not a full UI test (no click simulation) — just proves AppContext,
MainWindow, and all nine screens wire together without raising. Uses
well-formed but fake credentials so `require_live_credentials()` passes;
the fake Google service-account file then fails lazily inside
`load_live_students()`, which is designed to catch that and start with an
empty student list rather than crash (see app_context.py). Needs a real or
virtual display, same runtime requirement as the Playwright-driven
integration tests need a Chromium binary.
"""

from __future__ import annotations

import pytest


def test_app_launches_and_closes(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")

    monkeypatch.setenv("UDIFY_SQLITE_PATH", str(tmp_path / "smoke.sqlite3"))
    monkeypatch.setenv("UDIFY_DIAGNOSTICS_DIR", str(tmp_path / "diagnostics"))
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(tmp_path / "fake-service-account.json"))
    monkeypatch.setenv("GUJARAT_UDISE_LOGIN_URL", "https://example.invalid/gujarat")
    monkeypatch.setenv("GUJARAT_UDISE_SCHOOL_CODE", "school-code")
    monkeypatch.setenv("GUJARAT_UDISE_USERNAME", "user")
    monkeypatch.setenv("GUJARAT_UDISE_PASSWORD", "pw")
    monkeypatch.setenv("NATIONAL_UDISE_PLUS_LOGIN_URL", "https://example.invalid/national")
    monkeypatch.setenv("NATIONAL_UDISE_PLUS_USERNAME", "user")
    monkeypatch.setenv("NATIONAL_UDISE_PLUS_PASSWORD", "pw")

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
        # No real Google credentials are configured, so the OGR load fails
        # and is caught — an empty list, not a crash (app_context.py).
        assert ctx.demo_students == []
    finally:
        ctx.close()
