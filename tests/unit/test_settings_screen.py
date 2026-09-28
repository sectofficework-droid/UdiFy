"""Drives the real SettingsScreen widget end to end: types into fields,
clicks Save, and confirms .env actually gets written — not just that
write_env_values() works in isolation (see test_settings_writer.py).

Redirects src.config.settings_writer.PROJECT_ROOT to a tmp directory so
this never touches the real project's .env/credentials/.
"""

from __future__ import annotations

import pytest


def test_save_button_writes_env_and_masks_passwords_on_reload(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")

    monkeypatch.setattr("src.config.settings_writer.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("UDIFY_SQLITE_PATH", str(tmp_path / "settings_test.sqlite3"))
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
    from src.app.screens.settings_view import SettingsScreen

    app = QApplication.instance() or QApplication([])
    ctx = AppContext()
    try:
        screen = SettingsScreen(ctx)
        screen.ogr_id.setText("ogr-sheet-id-123")
        screen.udise_id.setText("udise-sheet-id-456")
        screen.pen_id.setText("pen-sheet-id-789")
        screen.gujarat_school_code.setText("24224100067")
        screen.gujarat_username.setText("school-user")
        screen.gujarat_password.setText("not-a-real-password")
        screen.national_username.setText("national-user")
        screen.national_password.setText("also-not-a-real-password")

        screen._save()

        env_file = tmp_path / ".env"
        assert env_file.exists()
        content = env_file.read_text(encoding="utf-8")
        assert "GOOGLE_SPREADSHEET_ID_OGR=ogr-sheet-id-123" in content
        assert "GOOGLE_SPREADSHEET_ID_UDISE=udise-sheet-id-456" in content
        assert "GOOGLE_SPREADSHEET_ID_PEN=pen-sheet-id-789" in content
        assert "GUJARAT_UDISE_USERNAME=school-user" in content
        assert "GUJARAT_UDISE_PASSWORD=not-a-real-password" in content
        assert "NATIONAL_UDISE_PLUS_USERNAME=national-user" in content
        assert "NATIONAL_UDISE_PLUS_PASSWORD=also-not-a-real-password" in content
        # UDIFY_ENVIRONMENT was never in the values passed to write_env_values.
        assert "UDIFY_ENVIRONMENT=LIVE" not in content

        assert "restart UdiFy" in screen.status_label.text()
        # Password fields never redisplay what was just saved.
        assert screen.gujarat_password.text() == ""
        assert screen.national_password.text() == ""
    finally:
        ctx.close()


def test_leaving_password_blank_on_resave_keeps_the_previous_value(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")

    monkeypatch.setattr("src.config.settings_writer.PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("UDIFY_SQLITE_PATH", str(tmp_path / "settings_test2.sqlite3"))
    monkeypatch.setenv("UDIFY_DIAGNOSTICS_DIR", str(tmp_path / "diagnostics2"))
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
    from src.app.screens.settings_view import SettingsScreen

    app = QApplication.instance() or QApplication([])
    ctx = AppContext()
    try:
        screen = SettingsScreen(ctx)
        screen.gujarat_password.setText("first-password")
        screen._save()

        # Simulate reopening Settings later: a fresh screen reload would
        # see the saved password via ctx.settings, but within the same
        # screen instance we just prove the in-memory "existing" value
        # survives an empty resave.
        screen.gujarat_school_code.setText("changed-school-code")
        screen._save()  # password field left blank this time

        content = (tmp_path / ".env").read_text(encoding="utf-8")
        assert "GUJARAT_UDISE_PASSWORD=first-password" in content
        assert "GUJARAT_UDISE_SCHOOL_CODE=changed-school-code" in content
    finally:
        ctx.close()
