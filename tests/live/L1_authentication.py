r"""L1 — authentication against both real government portals.

Drives the real adapters' `login()` against the configured login URLs and
reports whether each portal accepted the credentials. **Read-only**: it logs
in and stops. It does not create, edit, or submit anything.

    .venv\Scripts\python.exe tests\live\L1_authentication.py

A visible browser opens. **A CAPTCHA is expected on both portals**: type it
into the browser window and the script continues. Do not re-run this script
in a loop if it fails — repeated logins against a government portal can
trip fraud detection and get the school's real account flagged.
"""

from __future__ import annotations

from _live_common import banner, require_live_settings, show_config_summary

from playwright.sync_api import sync_playwright

from src.portals.base import AutomationPausedForUser
from src.portals.udise_gujarat.adapter import GujaratUDISEPortalAdapter
from src.portals.udise_plus.adapter import NationalUDISEPortalAdapter


def _attempt(label: str, url: str, make_adapter, login_args) -> str:
    """Log into one portal, handling a CAPTCHA as the pause it is.

    On `AutomationPausedForUser` the script simply waits for the operator
    and calls `login()` again. No monkey-patching is needed: the adapters'
    `_captcha_present()` checks the field's *value*, so once the code has
    been typed it returns False and the retry proceeds normally. That
    value-based behaviour is exactly why the 2026-09-26 live session fixed
    it that way.
    """
    page = browser.new_page()
    page.goto(url)
    adapter = make_adapter(page)

    for attempt in (1, 2):
        try:
            adapter.login(*login_args)
        except AutomationPausedForUser as exc:
            if attempt == 2:
                print(f"  {label}: captcha still unresolved after the second try.")
                return "FAILED"
            print(f"  {label}: CAPTCHA encountered - type it into the browser window.")
            print(f"         ({exc})")
            input("         Press Enter here once the captcha is typed... ")
            continue
        except Exception as exc:
            print(f"  {label}: FAILED - {type(exc).__name__}: {exc}")
            page.close()
            return "FAILED"
        print(f"  {label}: login accepted (landed on {page.url})")
        page.close()
        return "OK"

    page.close()
    return "FAILED"


def main() -> int:
    global browser
    settings = require_live_settings()
    show_config_summary(settings)

    results: dict[str, str] = {}
    with sync_playwright() as pw:
        # Never headless, per the spec's visible-browser criterion.
        browser = pw.chromium.launch(headless=False)
        try:
            banner("L1 - Gujarat UDISE (state portal)")
            results["gujarat"] = _attempt(
                "Gujarat UDISE",
                settings.gujarat_portal.login_url,
                lambda page: GujaratUDISEPortalAdapter(page, timeout_ms=60_000),
                (settings.gujarat_portal.school_code, settings.gujarat_portal.password),
            )

            banner("L1 - National UDISE+ (national portal)")
            results["national"] = _attempt(
                "National UDISE+",
                settings.national_portal.login_url,
                lambda page: NationalUDISEPortalAdapter(page, timeout_ms=60_000),
                (settings.national_portal.username, settings.national_portal.password),
            )
        finally:
            browser.close()

    banner("L1 result")
    for portal, outcome in results.items():
        print(f"  {portal:10} {outcome}")
    if all(o == "OK" for o in results.values()):
        print("\nPASSED - both real portals accepted the configured credentials.")
        print("Nothing was created, edited or submitted by this script.")
        return 0
    print("\nFAILED - see above. Check the Diagnostics log before re-running;")
    print("do not retry in a loop.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
