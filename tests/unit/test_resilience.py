"""Unit tests for src/engine/resilience.py's generic recovery classifier.

No browser needed — these simulate the exception types Playwright itself
raises, since the point is to verify classification/diagnostic-capture
behavior, not real portal interaction (that's covered by the fixture-
driven integration tests elsewhere).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.db.connection import connect
from src.db.diagnostics import get_diagnostic
from src.engine.resilience import (
    BrowserOrNetworkFailureError,
    RecoverableAutomationError,
    run_with_recovery,
)
from src.portals.base import AutomationPausedForUser, ConsequentialActionUnverifiedError


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


def test_happy_path_returns_value_unchanged(db_conn):
    result = run_with_recovery(
        lambda: 42, conn=db_conn, environment="MOCK", workflow="TEST",
    )
    assert result == 42


def test_automation_paused_for_user_passes_through_unchanged(db_conn):
    def raise_paused():
        raise AutomationPausedForUser("CAPTCHA present", checkpoint="login")

    with pytest.raises(AutomationPausedForUser):
        run_with_recovery(raise_paused, conn=db_conn, environment="MOCK", workflow="TEST")


def test_existing_portal_error_passes_through_unchanged(db_conn):
    def raise_unverified():
        raise ConsequentialActionUnverifiedError("Expected text never appeared")

    with pytest.raises(ConsequentialActionUnverifiedError):
        run_with_recovery(raise_unverified, conn=db_conn, environment="MOCK", workflow="TEST")


def test_timeout_error_becomes_recoverable_automation_error_with_diagnostic(db_conn):
    def raise_timeout():
        raise PlaywrightTimeoutError("Locator.click: Timeout 30000ms exceeded.")

    with pytest.raises(RecoverableAutomationError) as excinfo:
        run_with_recovery(
            raise_timeout, conn=db_conn, environment="MOCK", workflow="TEST",
            student_id="s-1",
        )

    assert excinfo.value.retry_allowed is True
    diagnostic = get_diagnostic(db_conn, excinfo.value.diagnostic_id)
    assert diagnostic is not None
    assert diagnostic["error_code"] == "PORTAL_TIMEOUT_OR_UNKNOWN_STATE"
    assert diagnostic["student_id"] == "s-1"


def test_other_playwright_error_becomes_browser_or_network_failure(db_conn):
    def raise_generic():
        raise PlaywrightError("Target page, context or browser has been closed")

    with pytest.raises(BrowserOrNetworkFailureError) as excinfo:
        run_with_recovery(raise_generic, conn=db_conn, environment="MOCK", workflow="TEST")

    diagnostic = get_diagnostic(db_conn, excinfo.value.diagnostic_id)
    assert diagnostic is not None
    assert diagnostic["error_code"] == "BROWSER_OR_NETWORK_FAILURE"
