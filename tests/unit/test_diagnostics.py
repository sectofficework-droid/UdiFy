"""Tests for the logging/diagnostics system itself (RULEBOOK.md §L10:
"do not assume logging works merely because logging code exists").
"""

from __future__ import annotations

import json
import logging

import pytest

from src.db.connection import connect
from src.db.diagnostics import get_diagnostic, list_recent_diagnostics
from src.diagnostics.capture import capture_failure
from src.diagnostics.diagnostic_id import new_diagnostic_id
from src.diagnostics.logging_setup import SESSION_ID, configure_logging, get_logger, log_event
from src.diagnostics.redaction import redact_mapping
from src.sheets.models import SheetRowRef
from src.sheets.repository import MockSheetsRepository, SheetWriteError


@pytest.fixture()
def conn(tmp_path):
    connection = connect(tmp_path / "test.sqlite3")
    yield connection
    connection.close()


@pytest.fixture()
def logger(tmp_path):
    configure_logging(tmp_path / "diagnostics", log_level="DEBUG", force=True)
    return get_logger("test")


def test_diagnostic_id_format_and_uniqueness():
    ids = {new_diagnostic_id() for _ in range(50)}
    assert all(i.startswith("ERR-") for i in ids)
    assert len(ids) > 1  # extremely unlikely to all collide


def test_redact_mapping_strips_sensitive_keys():
    data = {
        "username": "sunil.pradhan",
        "password": "hunter2",
        "GUJARAT_UDISE_PASSWORD": "s3cret",
        "aadhaar": "123412341234",
        "nested": {"api_key": "abc", "safe": "value"},
    }
    redacted = redact_mapping(data)
    assert redacted["username"] == "sunil.pradhan"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["GUJARAT_UDISE_PASSWORD"] == "***REDACTED***"
    assert redacted["aadhaar"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "value"


def test_log_event_writes_structured_json_to_file(tmp_path):
    diag_dir = tmp_path / "diag"
    configure_logging(diag_dir, log_level="DEBUG", force=True)
    logger = get_logger("test.structured")
    log_event(logger, logging.ERROR, "something failed", error_code="X1", student_id="s-1")

    log_file = diag_dir / "udify.log"
    assert log_file.exists()
    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    record = json.loads(lines[-1])
    assert record["message"] == "something failed"
    assert record["level"] == "ERROR"
    assert record["session_id"] == SESSION_ID
    assert record["fields"]["error_code"] == "X1"
    assert record["fields"]["student_id"] == "s-1"


def test_log_event_redacts_secret_shaped_fields(tmp_path):
    diag_dir = tmp_path / "diag"
    configure_logging(diag_dir, log_level="DEBUG", force=True)
    logger = get_logger("test.secrets")
    log_event(logger, logging.ERROR, "login failed", password="hunter2", username="ok")

    log_file = diag_dir / "udify.log"
    content = log_file.read_text(encoding="utf-8")
    assert "hunter2" not in content
    last_record = json.loads(
        [line for line in content.splitlines() if line.strip()][-1]
    )
    assert last_record["fields"]["password"] == "***REDACTED***"
    assert last_record["fields"]["username"] == "ok"


def test_capture_failure_persists_and_returns_diagnostic_id(conn, tmp_path):
    configure_logging(tmp_path / "diag", log_level="DEBUG", force=True)
    diagnostic_id = capture_failure(
        conn,
        summary="Aadhaar consent dialog detected",
        environment="MOCK",
        severity="WARNING",
        retry_allowed=False,
        workflow="PEN_NEW_ENTRY",
        student_id="s-1",
        expected_state="Enrolment Profile form",
        observed_state="Consent for demographic authentication dialog",
        url="https://sdms.udiseplus.gov.in/g2/#/enrolment",
        error_code="AUTOMATION_PAUSED_FOR_USER",
    )
    assert diagnostic_id.startswith("ERR-")
    row = get_diagnostic(conn, diagnostic_id)
    assert row is not None
    assert row["summary"] == "Aadhaar consent dialog detected"
    assert row["retry_allowed"] == 0
    assert row["environment"] == "MOCK"

    recent = list_recent_diagnostics(conn)
    assert any(r["diagnostic_id"] == diagnostic_id for r in recent)


def test_deliberately_triggered_sheets_failure_is_captured(tmp_path):
    """RULEBOOK §L10: deliberately trigger a known error and confirm it's
    captured with the right context, no leaked secrets."""
    diag_dir = tmp_path / "diag"
    configure_logging(diag_dir, log_level="DEBUG", force=True)

    repo = MockSheetsRepository()
    row = SheetRowRef(spreadsheet="UDISE_Entry_(State)", tab="PH2", row_number=5)
    repo.simulate_write_failure(times=1)
    with pytest.raises(SheetWriteError):
        repo.write_cell(row, "UDISE No", "242241000672631042")

    log_file = diag_dir / "udify.log"
    content = log_file.read_text(encoding="utf-8")
    last_record = json.loads([line for line in content.splitlines() if line.strip()][-1])
    assert last_record["level"] == "ERROR"
    assert last_record["fields"]["error_code"] == "SHEETS_WRITE_FAILED"
    assert last_record["fields"]["column"] == "UDISE No"
    # The real student UID value isn't a secret, but confirm the log is
    # genuinely structured (not a bare "Element not found" string, §L2/L3).
    assert "row_ref" in last_record["fields"]
