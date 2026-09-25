"""Session expiry / timeout / unknown page-state / browser-crash mock
scenarios (TODO.md mock scenario checklist, both portals) — using REAL
Playwright timeouts and a real closed browser/page, routed through
run_with_recovery(), not just simulated exception objects (that part is
already covered by tests/unit/test_resilience.py; this is the integration
proof that the real thing actually gets classified and captured
correctly).

"Session expiry" and "unknown page/state" share the same observable
signature here deliberately — spec never confirms distinguishing text for
either (see resilience.py's own docstring), so both are modeled the same
way: the expected next element never appears, because the portal
redirected somewhere else (expired session) or shows a screen this
adapter doesn't recognize (unknown state). "Timeout" is the same
mechanism at the network/rendering level. All three surface as a
Playwright TimeoutError to the caller.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from src.db.connection import connect
from src.db.diagnostics import get_diagnostic
from src.engine.resilience import (
    BrowserOrNetworkFailureError,
    RecoverableAutomationError,
    run_with_recovery,
)
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter

GUJARAT_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "gujarat_udise" / "new_entry.html"
)
NATIONAL_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "udise_plus" / "new_pen_entry.html"
)


@pytest.fixture()
def db_conn(tmp_path):
    conn = connect(tmp_path / "test.sqlite3")
    yield conn
    conn.close()


def test_gujarat_session_expiry_or_unknown_state_is_captured_and_recoverable(db_conn):
    """Simulates the portal having silently redirected the session
    somewhere unrecognized (expired session / unknown page): the page
    genuinely has none of the expected login fields, so the adapter's
    very first (unwrapped) `.fill()` call times out for real — a real
    Playwright TimeoutError, not a mocked one."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto("about:blank")  # stands in for "redirected to an unrecognized page"
            adapter = GujaratUDISEPortalAdapter(page, timeout_ms=500)

            with pytest.raises(RecoverableAutomationError) as excinfo:
                run_with_recovery(
                    lambda: adapter.login("24224100067", "not-a-real-password"),
                    conn=db_conn, environment="MOCK", workflow="TEST_SESSION_EXPIRY",
                    student_id="s-session-1",
                )

            diagnostic = get_diagnostic(db_conn, excinfo.value.diagnostic_id)
            assert diagnostic is not None
            assert diagnostic["error_code"] == "PORTAL_TIMEOUT_OR_UNKNOWN_STATE"
            assert diagnostic["workflow"] == "TEST_SESSION_EXPIRY"
        finally:
            browser.close()


def test_national_unknown_page_state_is_captured_and_recoverable(db_conn):
    """Same scenario on the National adapter: the expected form fields
    genuinely don't exist on the current page, so the very first call
    times out for real before ever reaching a success/failure text
    check."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page()
            page.goto("about:blank")
            adapter = NationalUDISEPortalAdapter(page, timeout_ms=500)

            with pytest.raises(RecoverableAutomationError) as excinfo:
                run_with_recovery(
                    lambda: adapter.login("sunil.pradhan", "not-a-real-password"),
                    conn=db_conn, environment="MOCK", workflow="TEST_UNKNOWN_STATE",
                )

            diagnostic = get_diagnostic(db_conn, excinfo.value.diagnostic_id)
            assert diagnostic is not None
            assert diagnostic["error_code"] == "PORTAL_TIMEOUT_OR_UNKNOWN_STATE"
        finally:
            browser.close()


def test_browser_crash_during_action_is_captured_as_network_failure(db_conn):
    """A closed browser/page mid-action is Playwright's own signature for
    "the browser process is gone" — the generic (non-timeout) failure
    path, never silently swallowed."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(f"file:///{GUJARAT_FIXTURE.as_posix()}")
        adapter = GujaratUDISEPortalAdapter(page, timeout_ms=2000)
        browser.close()  # simulate the crash: browser is gone mid-run

        with pytest.raises(BrowserOrNetworkFailureError) as excinfo:
            run_with_recovery(
                lambda: adapter.login("24224100067", "not-a-real-password"),
                conn=db_conn, environment="MOCK", workflow="TEST_BROWSER_CRASH",
            )

        diagnostic = get_diagnostic(db_conn, excinfo.value.diagnostic_id)
        assert diagnostic is not None
        assert diagnostic["error_code"] == "BROWSER_OR_NETWORK_FAILURE"
