"""Proves portal_factory opens the real configured portals, not a mock page.

Before 2026-09-27, every GUI screen hardcoded a local mock-page path — a
defect that survived review because nothing exercised the real code path.
This drives that real code path with the browser and network stubbed at
the outermost boundary only — the URL resolution, credential requirement,
adapter construction and login call are all the app's real code
(RULEBOOK.md J12C level 3: integration, not level 1 inspection).

No network call is made and no real credential is used.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.app.portal_factory import (
    LIVE_TIMEOUT_MS,
    PortalSession,
    PortalSetupError,
    open_portal_session,
)
from src.config.settings import (
    Environment,
    GoogleSheetsConfig,
    GujaratPortalCredentials,
    NationalPortalCredentials,
    Settings,
)
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter


class _FakePage:
    def __init__(self, log: list[str]):
        self.log = log
        self.closed = False

    def goto(self, url: str) -> None:
        self.log.append(url)

    def close(self) -> None:
        self.closed = True

    def title(self) -> str:
        return "fake"

    @property
    def url(self) -> str:
        return "about:blank"


class _FakeBrowser:
    def __init__(self):
        self.visited: list[str] = []
        self.pages: list[_FakePage] = []

    def new_page(self) -> _FakePage:
        page = _FakePage(self.visited)
        self.pages.append(page)
        return page


def _live_settings(**portal_overrides) -> Settings:
    return Settings(
        environment=Environment.LIVE,
        sheets=GoogleSheetsConfig(
            service_account_file="credentials/service-account.json",
            spreadsheet_id_ogr="ogr",
            spreadsheet_id_udise="udise",
            spreadsheet_id_pen="pen",
        ),
        gujarat_portal=GujaratPortalCredentials(
            login_url="https://gujarat.example.invalid/login",
            school_code="school-code",
            username="user",
            password="pw",
        ),
        national_portal=NationalPortalCredentials(
            login_url="https://national.example.invalid/login",
            username="user",
            password="pw",
        ),
        diagnostics_dir=Path("diagnostics"),
        log_level="INFO",
        sqlite_path=Path("unused.sqlite3"),
    )


def test_live_session_navigates_to_the_configured_real_urls(monkeypatch):
    """The core regression guard.

    Before the fix, a LIVE-configured app navigated to
    file:///.../tests/fixtures/*.html. This asserts the real configured
    URLs are the ones actually opened.
    """
    browser = _FakeBrowser()
    # Stub only the browser-touching call inside login(); everything else —
    # URL resolution, credential checks, adapter construction, timeout
    # selection — is the app's real code.
    monkeypatch.setattr(GujaratUDISEPortalAdapter, "login", lambda *a, **k: None)
    monkeypatch.setattr(NationalUDISEPortalAdapter, "login", lambda *a, **k: None)

    session, owned = open_portal_session(_live_settings(), browser)

    assert owned is None, "a caller-supplied browser must not be claimed as owned"
    assert browser.visited == [
        "https://gujarat.example.invalid/login",
        "https://national.example.invalid/login",
    ]
    assert all("file:///" not in url for url in browser.visited)
    assert session.gujarat.timeout_ms == LIVE_TIMEOUT_MS
    assert session.national.timeout_ms == LIVE_TIMEOUT_MS
    assert isinstance(session.gujarat, GujaratUDISEPortalAdapter)
    assert isinstance(session.national, NationalUDISEPortalAdapter)


def test_live_login_receives_configured_credentials(monkeypatch):
    """Proves credentials are read from Settings and actually passed to the
    real login() calls — not that login() is merely invoked."""
    browser = _FakeBrowser()
    seen: dict[str, tuple] = {}

    def fake_gujarat_login(self, school_code, password):
        seen["gujarat"] = (school_code, password)

    def fake_national_login(self, username, password):
        seen["national"] = (username, password)

    monkeypatch.setattr(GujaratUDISEPortalAdapter, "login", fake_gujarat_login)
    monkeypatch.setattr(NationalUDISEPortalAdapter, "login", fake_national_login)

    open_portal_session(_live_settings(), browser)

    assert seen["gujarat"] == ("school-code", "pw")
    assert seen["national"] == ("user", "pw")


def test_live_missing_url_raises_before_any_navigation(monkeypatch):
    """Must fail before opening a page — not after."""
    browser = _FakeBrowser()
    settings = _live_settings()
    broken = replace(
        settings,
        gujarat_portal=replace(settings.gujarat_portal, login_url=None),
    )
    with pytest.raises(PortalSetupError) as exc:
        open_portal_session(broken, browser)
    assert "GUJARAT_UDISE_LOGIN_URL" in str(exc.value)
    assert browser.visited == [], "no page may be opened when LIVE is misconfigured"


def test_live_non_http_url_is_rejected(monkeypatch):
    browser = _FakeBrowser()
    settings = _live_settings()
    broken = replace(
        settings,
        national_portal=replace(settings.national_portal, login_url="file:///etc/passwd"),
    )
    with pytest.raises(PortalSetupError):
        open_portal_session(broken, browser)
    assert browser.visited == []


def test_session_close_closes_both_pages():
    session = PortalSession(
        gujarat=GujaratUDISEPortalAdapter(_FakePage([])),
        national=NationalUDISEPortalAdapter(_FakePage([])),
    )
    session.close()
    assert session.gujarat.page.closed is True
    assert session.national.page.closed is True
