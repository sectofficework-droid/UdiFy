"""Unit tests for src/config/settings_writer.py — the .env-persistence
layer behind the Settings screen's editable Google Sheets/portal-login
form (spec: configure LIVE credentials through the GUI instead of
hand-editing .env each time)."""

from __future__ import annotations

from src.config.settings_writer import import_service_account_file, write_env_values


def test_write_env_values_creates_file_when_missing(tmp_path):
    env_file = tmp_path / ".env"
    write_env_values({"GOOGLE_SPREADSHEET_ID_OGR": "abc123"}, env_file=env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "GOOGLE_SPREADSHEET_ID_OGR=abc123" in content


def test_write_env_values_updates_existing_key_in_place(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "UDIFY_ENVIRONMENT=MOCK\nGOOGLE_SPREADSHEET_ID_OGR=old-value\n", encoding="utf-8"
    )

    write_env_values({"GOOGLE_SPREADSHEET_ID_OGR": "new-value"}, env_file=env_file)

    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines.count("GOOGLE_SPREADSHEET_ID_OGR=new-value") == 1
    assert "GOOGLE_SPREADSHEET_ID_OGR=old-value" not in lines
    assert "UDIFY_ENVIRONMENT=MOCK" in lines  # untouched


def test_write_env_values_preserves_comments_and_unrelated_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\nUDIFY_LOG_LEVEL=INFO\n\nGOOGLE_SPREADSHEET_ID_OGR=x\n",
        encoding="utf-8",
    )

    write_env_values({"GOOGLE_SPREADSHEET_ID_OGR": "y"}, env_file=env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "# a comment" in content
    assert "UDIFY_LOG_LEVEL=INFO" in content
    assert "GOOGLE_SPREADSHEET_ID_OGR=y" in content
    assert "GOOGLE_SPREADSHEET_ID_OGR=x" not in content


def test_write_env_values_appends_new_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("UDIFY_ENVIRONMENT=MOCK\n", encoding="utf-8")

    write_env_values(
        {"GUJARAT_UDISE_USERNAME": "user1", "GUJARAT_UDISE_PASSWORD": "not-a-real-password"},
        env_file=env_file,
    )

    content = env_file.read_text(encoding="utf-8")
    assert "GUJARAT_UDISE_USERNAME=user1" in content
    assert "GUJARAT_UDISE_PASSWORD=not-a-real-password" in content
    assert "UDIFY_ENVIRONMENT=MOCK" in content


def test_write_env_values_can_clear_a_key_to_empty(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NATIONAL_UDISE_PLUS_USERNAME=someone\n", encoding="utf-8")

    write_env_values({"NATIONAL_UDISE_PLUS_USERNAME": ""}, env_file=env_file)

    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert "NATIONAL_UDISE_PLUS_USERNAME=" in lines


def test_import_service_account_file_copies_into_credentials_dir(tmp_path):
    source = tmp_path / "downloaded-key.json"
    source.write_text('{"type": "service_account"}', encoding="utf-8")
    dest_dir = tmp_path / "credentials"

    result = import_service_account_file(source, dest_dir=dest_dir)

    assert result == (dest_dir / "service-account.json").resolve()
    assert result.read_text(encoding="utf-8") == '{"type": "service_account"}'
