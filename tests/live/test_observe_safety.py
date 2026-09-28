"""Observation mode MUST never be able to submit to a government portal.

`explore_portal.py` is the tool used to observe the real UDISE/PEN portals.
Its entire safety guarantee is that a run cannot commit a change: filling
fields is fine, saving is not. That guarantee is worth nothing if the
blocker silently stops matching, so it is tested here for real — against a
real browser, using the real `INJECT_BLOCKER` from the explorer.

This test exists because of a real bug it now prevents: the JS regex was
built with over-escaped backslashes, so the word-boundary `\\b` never
matched and the pattern matched almost any text containing the letter
"s" — which blocked "Students Module" and broke navigation entirely. The
failure was silent and would have looked like a portal problem.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "tests" / "live") not in sys.path:
    sys.path.insert(0, str(_ROOT / "tests" / "live"))

from explore_portal import BLOCK_TEXT, INJECT_BLOCKER, is_blocked_method  # noqa: E402

FIXTURE = Path(__file__).with_name("fixtures") / "blocker_test.html"

MUST_BLOCK = ["save", "submit", "confirm", "add", "create", "gen", "finalize", "lateSave"]
MUST_CLICK = ["nav", "go", "signin", "benignSubmit"]


@pytest.fixture(scope="module")
def blocked_page():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        page.add_init_script(INJECT_BLOCKER)
        page.goto(FIXTURE.as_uri())
        page.wait_for_function("window.__lateReady === true", timeout=10_000)
        yield page
        browser.close()


# ---------------- pattern correctness (pure, fast) ----------------


@pytest.mark.parametrize(
    "text",
    ["SAVE STUDENT", "Submit", "Confirm Transfer Request", "Add New Student",
     "Finalize", "Create Request", "Generate Release Request", "Save Student (late)"],
)
def test_block_text_matches_committing_labels(text):
    assert BLOCK_TEXT.match(text), f"{text!r} should be treated as committing"


@pytest.mark.parametrize(
    "text",
    ["Students Module", "Student Module", "Go", "Cancel", "Sign In", "View/Manage",
     "Track By Details", "View Details", "Search"],
)
def test_block_text_does_not_match_navigation_labels(text):
    """Regression guard for the escaping bug: without a working word
    boundary this matched navigation labels too."""
    assert not BLOCK_TEXT.match(text), f"{text!r} must stay clickable"


@pytest.mark.parametrize(
    "name",
    ["submit_manual_birth_details", "submit_cts_details", "save_current_tab",
     "confirm_transfer_request", "complete_profile_preview",
     "generate_release_request", "submit_release_admission_detail",
     "confirm_identity_details"],
)
def test_committing_methods_are_blocked(name):
    assert is_blocked_method(name), f"{name!r} should be refused"


@pytest.mark.parametrize(
    "name",
    ["open_students_module", "open_add_student", "open_student_new_entry",
     "dismiss_pending_notifications", "open_tab", "fill_tab", "read_generated_uid",
     "search_existing_student_by_uid", "find_transfer_request", "login",
     "check_aadhaar_availability", "open_track_by_details", "global_student_search_by_pen",
     "open_hos_details", "get_student_release_details", "open_sent_requests",
     "find_sent_request", "search_for_nd_reconciliation"],
)
def test_navigation_and_read_methods_are_allowed(name):
    """Regression guard: a substring pattern blocked the read-only
    `read_generated_uid` and the harmless `find_transfer_request`. An
    allowlist is used instead, and this pins the read-only set."""
    assert not is_blocked_method(name), f"{name!r} must stay allowed"


# ---------------- live DOM behaviour ----------------


@pytest.mark.parametrize("control_id", MUST_BLOCK)
def test_committing_control_is_disarmed(blocked_page, control_id):
    locator = blocked_page.locator(f"#{control_id}")
    expect(locator).to_have_attribute("data-udify-blocked", "1")
    assert locator.evaluate("e => getComputedStyle(e).pointerEvents") == "none"


@pytest.mark.parametrize("control_id", MUST_BLOCK)
def test_committing_control_cannot_reach_the_page_handler(blocked_page, control_id):
    """force=True bypasses Playwright's actionability checks, so this proves
    the page's own listener never fires — not merely that the click is
    awkward."""
    blocked_page.locator(f"#{control_id}").click(force=True, timeout=5_000)
    log = blocked_page.locator("#log").inner_text()
    assert "CLICKED" not in log, f"a committing control was clicked: {log!r}"


@pytest.mark.parametrize("control_id", MUST_CLICK)
def test_navigation_control_still_works(blocked_page, control_id):
    blocked_page.locator(f"#{control_id}").click(timeout=5_000)
    log = blocked_page.locator("#log").inner_text()
    assert "CLICKED" in log, f"navigation control #{control_id} was wrongly blocked"


def test_a_link_still_navigates(blocked_page):
    blocked_page.locator("a.btn").click(timeout=5_000)
    assert "Cancel" in blocked_page.locator("#log").inner_text()


def test_form_fields_remain_typeable(blocked_page):
    """Observation must allow filling — that is the whole point of
    'interactive but never submits'."""
    blocked_page.fill("#name", "TEST OBSERVATION")
    blocked_page.fill("#dob", "01-01-2020")
    assert blocked_page.input_value("#name") == "TEST OBSERVATION"
    assert blocked_page.input_value("#dob") == "01-01-2020"


def test_blocker_survives_navigation(blocked_page):
    """The init script must re-arm on every page load, or a multi-page
    portal walk would lose protection after the first click."""
    blocked_page.goto(FIXTURE.as_uri())
    blocked_page.wait_for_function("window.__lateReady === true", timeout=10_000)
    expect(blocked_page.locator("#save")).to_have_attribute("data-udify-blocked", "1")
    blocked_page.locator("#submit").click(force=True, timeout=5_000)
    assert "CLICKED" not in blocked_page.locator("#log").inner_text()


def test_late_added_committing_control_is_caught(blocked_page):
    """A control injected after load (a modal, a wizard step) must also be
    disarmed — that is what the MutationObserver is for."""
    expect(blocked_page.locator("#lateSave")).to_have_attribute("data-udify-blocked", "1")
    blocked_page.locator("#lateSave").click(force=True, timeout=5_000)
    assert "CLICKED LATE" not in blocked_page.locator("#log").inner_text()
