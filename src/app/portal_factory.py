"""Environment-aware portal setup — the single place that decides whether
a run drives the REAL government portals or the local MOCK fixtures.

This module exists because of a real, structural defect found in review on
2026-09-27: `AppContext` correctly builds a real `GoogleSheetsRepository`
when `UDIFY_ENVIRONMENT=LIVE`, but every GUI screen hardcoded
`file:///.../tests/fixtures/...` and passed `environment="MOCK"` as a
literal. The released application therefore opened a local HTML file,
logged into it with a mock password, and wrote that result into the school's
REAL Google Sheet. `settings.py` parsed `GUJARAT_UDISE_LOGIN_URL` /
`NATIONAL_UDISE_PLUS_LOGIN_URL` but nothing ever consumed them.

RULEBOOK.md J9 (scope control) and K3 (smallest correct change) both point
at fixing this at the seam rather than sprinkling environment checks through
each screen. So: screens ask this module for portals, and it alone decides
real-vs-mock from the same `Settings` object the rest of the app already
uses. One decision, one place, impossible for a screen to get wrong by
accident.

Two invariants this preserves, both deliberate:

1. **Never headless.** Both branches pass `headless=False` explicitly. The
   spec's "visible/headed browser operation" acceptance criterion is not
   negotiable without an explicit authorized exception, and no such
   exception has been granted.
2. **No invented fallback.** If LIVE is configured but something required is
   missing (a login URL, a credential), this raises rather than quietly
   driving a mock. A silent mock fallback inside a LIVE run is precisely
   the failure that made this defect dangerous in the first place — it
   *looks* like it worked.

The CAPTCHA contract is preserved verbatim: both real portals raise
`AutomationPausedForUser` from `login()` when a CAPTCHA is present, which
the workers already surface as a deliberate operator pause (spec I), not an
error. This factory does not attempt to solve or bypass a CAPTCHA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.sync_api import Browser, Page, sync_playwright

from src.app.mock_fixtures import GUJARAT_FIXTURE, NATIONAL_FIXTURE
from src.config.settings import Environment, Settings
from src.diagnostics.logging_setup import get_logger, log_event
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter

_logger = get_logger("app.portal_factory")

# Fixture runs are local files; give them a short leash so a broken selector
# fails the test in seconds. Real portals are genuinely slow and network-
# dependent, so they get a much longer one.
MOCK_TIMEOUT_MS = 5_000
LIVE_TIMEOUT_MS = 60_000

# Never used as a real credential — the fixtures have no real login, and a
# clearly-fake literal is required by the spec's "no credential hardcoding"
# acceptance criterion.
MOCK_SCHOOL_CODE = "mock-school-code"
MOCK_USERNAME = "mock-username"
MOCK_PASSWORD = "mock-password"


class PortalSetupError(Exception):
    """LIVE mode is configured but the app cannot actually reach a real
    portal. Raised instead of silently degrading to the mock fixtures."""


@dataclass
class PortalSession:
    """One page + adapter per portal, already navigated and logged in."""

    gujarat: GujaratUDISEPortalAdapter
    national: NationalUDISEPortalAdapter
    is_live: bool

    def close(self) -> None:
        for adapter in (self.gujarat, self.national):
            try:
                adapter.page.close()
            except Exception:  # pragma: no cover - best-effort teardown
                pass


def _require(value: str | None, *, name: str, portal: str) -> str:
    if not value or not value.strip():
        raise PortalSetupError(
            f"{portal}: {name} is not configured, but UDIY_ENVIRONMENT=LIVE. "
            f"Set {name} in .env (or via the app's Settings screen) and "
            f"restart. Refusing to fall back to the mock fixtures — a live "
            f"run against mock pages would write mock results to the real "
            f"spreadsheets."
        )
    return value.strip()


def _validate_login_url(url: str, *, portal: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        raise PortalSetupError(
            f"{portal}: login URL must start with http:// or https:// "
            f"(got {cleaned!r}). Refusing to navigate anywhere unexpected."
        )
    return cleaned


def open_portal_session(
    settings: Settings, browser: Browser | None = None
) -> tuple[PortalSession, Browser | None]:
    """Return a logged-in PortalSession, and the browser to close.

    Pass `browser` to reuse one the caller already opened (the GUI does,
    so both portals share a single visible window). Pass None to have one
    opened here and closed by the caller via the returned browser.
    """
    owns_browser = browser is None
    if browser is None:
        browser = sync_playwright().start().chromium.launch(headless=False)

    is_live = settings.environment is Environment.LIVE

    if is_live:
        log_event(
            _logger, logging.WARNING,
            "opening REAL government portals (LIVE) — this run can write to "
            "the live UDISE/PEN registers and the real OGR/UDISE/PEN sheets",
            gujarat_url=settings.gujarat_portal.login_url,
            national_url=settings.national_portal.login_url,
        )
        gujarat_url = _validate_login_url(
            _require(
                settings.gujarat_portal.login_url,
                name="GUJARAT_UDISE_LOGIN_URL", portal="Gujarat UDISE",
            ),
            portal="Gujarat UDISE",
        )
        national_url = _validate_login_url(
            _require(
                settings.national_portal.login_url,
                name="NATIONAL_UDISE_PLUS_LOGIN_URL", portal="National UDISE+",
            ),
            portal="National UDISE+",
        )
        timeout_ms = LIVE_TIMEOUT_MS
    else:
        log_event(_logger, logging.INFO, "opening MOCK portal fixtures")
        gujarat_url = f"file:///{GUJARAT_FIXTURE.as_posix()}"
        national_url = f"file:///{NATIONAL_FIXTURE.as_posix()}"
        timeout_ms = MOCK_TIMEOUT_MS

    gujarat_page = browser.new_page()
    gujarat_page.goto(gujarat_url)
    gujarat = GujaratUDISEPortalAdapter(gujarat_page, timeout_ms=timeout_ms)

    national_page = browser.new_page()
    national_page.goto(national_url)
    national = NationalUDISEPortalAdapter(national_page, timeout_ms=timeout_ms)

    # login() raises AutomationPausedForUser on a CAPTCHA, which callers
    # already handle as a deliberate operator pause. Credentials never reach
    # the log — log_event redacts by key name (RULEBOOK.md J6).
    if is_live:
        gujarat.login(
            _require(
                settings.gujarat_portal.school_code,
                name="GUJARAT_UDISE_SCHOOL_CODE", portal="Gujarat UDISE",
            ),
            _require(
                settings.gujarat_portal.password,
                name="GUJARAT_UDISE_PASSWORD", portal="Gujarat UDISE",
            ),
        )
        national.login(
            _require(
                settings.national_portal.username,
                name="NATIONAL_UDISE_PLUS_USERNAME", portal="National UDISE+",
            ),
            _require(
                settings.national_portal.password,
                name="NATIONAL_UDISE_PLUS_PASSWORD", portal="National UDISE+",
            ),
        )
    else:
        gujarat.login(MOCK_SCHOOL_CODE, MOCK_PASSWORD)
        national.login(MOCK_USERNAME, MOCK_PASSWORD)

    return PortalSession(gujarat=gujarat, national=national, is_live=is_live), (
        browser if owns_browser else None
    )
