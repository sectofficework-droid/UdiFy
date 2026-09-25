# TODO.md — UdiFy

> Per RULEBOOK.md §E.5. Phased checklist + approval gates + backlog. Gate
> trigger phrases are exactly as defined in RULEBOOK.md §F — do not advance
> on "continue"/"ok go"/a passed test.

## Phase status

| Phase | Status | Gate trigger |
|---|---|---|
| DISCOVERY | Distilled from existing spec — see DISCOVERY.md | **"approve discovery"** |
| CLARIFY | Bundled round completed 2026-09-25 (git init, secrets approach, stack) | n/a |
| PLANNING | **Approved** ("approve plan", 2026-09-25) | **"approve plan"** ✅ |
| DESIGN FIXED | **Approved** ("approve design", 2026-09-25) | **"approve design"** ✅ |
| UI DESIGN CONFIRMED | **Closed** ("code it", 2026-09-25) | **"UI is final" / "start backend"** ✅ |
| CODING | **Mock-first build order complete** (steps 1-16 below, 2026-09-25) — stopped at the Live Verification Gate (step 17) per the standing instruction to complete the whole project autonomously; live credential configuration and controlled live verification remain out of scope without the user present | **"code it"** ✅ |
| TESTING | Continuous throughout CODING per RULEBOOK §L/§J13 (60/60 unit+integration tests passing, including a dedicated UI-change resilience pass) — not the same as the formal TESTING gate, which still awaits its own trigger phrase | **"run tests" / "test it"** |
| RELEASE | Not started | **"approve release"** |
| OPERATE | Not started | automatic after approved release |

## Build order — mock-first (decision 2026-09-25, master spec "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION")

**Real Google Sheets / government-portal credentials are explicitly NOT a
prerequisite for any step below.** Build and fully test against mocks;
real credentials are configured only for the separate Live Verification
Gate phase at the end. Every external dependency is reached through an
interface (`StudentSheetRepository`, `GujaratUDISEPortalAdapter`,
`NationalUDISEPortalAdapter` — DB-DESIGN.md §C.6), with a `MockSheetsRepository`
and mocked/fixture portal pages as the primary implementation target.

1. [x] Local application foundation — `src/config/settings.py`
   (MOCK/LIVE switch, `.env` loading via python-dotenv, `.env.example`
   template, `require_live_credentials()` guard), `requirements.txt`
   pinned to real installed versions, `.venv` created, Playwright
   Chromium confirmed present. **Logging bootstrap** —
   `src/diagnostics/logging_setup.py` (centralized structured JSON
   logging, session-id correlation, global `sys.excepthook`),
   `src/diagnostics/redaction.py` (secret-shaped-key redaction on every
   log line, RULEBOOK §L8/§J6), `src/diagnostics/diagnostic_id.py`,
   `src/diagnostics/capture.py` + `src/db/diagnostics.py` (unified
   failure capture: log + persist + return a diagnostic ID). Retrofitted
   into `src/sheets/repository.py` and `src/db/events.py` so no failure
   path in either module raises silently. 6 dedicated tests
   (`tests/unit/test_diagnostics.py`) including a deliberately-triggered-
   failure test per RULEBOOK §L10. This was built *after* steps 3-4
   below, not before — a real process deviation from RULEBOOK §L1
   ("design it during development, alongside the change itself"), caught
   by the user asking whether debug logging was enabled; realigned per
   §0.3 rather than left for later. 24/24 unit tests passing.
2. [x] Normalized student data model — `src/sheets/models.py`
   (`Student`, `SheetRowRef`).
3. [x] `StudentSheetRepository` interface + `MockSheetsRepository` (full
   behavior: find by name/UID/PEN, row values/color read+write,
   idempotent duplicate-write prevention, simulated write/network/
   verification failure) + `GoogleSheetsRepository` (interface-complete,
   real Google API calls deliberately `NotImplementedError` until the
   Live Verification Gate — never silently stubbed as working).
   11 unit tests, all passing (`tests/unit/test_sheets_repository.py`).
4. [x] SQLite state/logging layer — `src/db/schema.py` (full schema, all
   8 tables from DB-DESIGN.md §B, `environment` field everywhere
   required), `src/db/connection.py`, `src/db/events.py` (append-only
   `pen_case_events`: controlled statuses/event codes/transitions,
   mandatory-field validation, tamper-evident hash chain). 7 unit tests,
   all passing (`tests/unit/test_events.py`) — caught and fixed a real
   bug (case-cycle continuity) via the tests before it reached the
   workflow engine.
5. Browser/session manager (Playwright, headed) — built to run against
   mocked/fixture pages first.
6. [~] `GujaratUDISEPortalAdapter` — `src/portals/base.py` (shared
   PortalName/exceptions incl. `AutomationPausedForUser`,
   `UnknownPortalStateError`, `ConsequentialActionUnverifiedError`) +
   `src/portals/udise_gujarat/adapter.py`: New Entry (login, manual birth
   route, CTS details, generic label-driven tab fill/save for
   Personal/Education/Bank/Scholarship & Facility/Health & CWSN) and
   Import/transfer-request (search by UID, confirm transfer, verify
   success message) — spec §W/§X. Every selector is role/label/exact-text
   based, never CSS/ID (spec Final Authority §B). Verified against a real
   local Playwright session driving an HTML fixture
   (`tests/fixtures/gujarat_udise/new_entry.html`,
   `tests/integration/test_gujarat_adapter.py`) — not just unit-tested in
   isolation. 2 real bugs found and fixed by this: (1) `Locator.is_visible()`
   doesn't poll/wait in Playwright, only `expect(...).to_be_visible()`
   does — verified against the installed API before relying on it; (2)
   `get_by_text()` does case-insensitive substring matching by default,
   so "Student New Entry" ambiguously matched both a button and an
   all-caps heading — fixed with `exact=True` throughout. Open item
   flagged inline: the spec confirms Personal tab's save button is
   literally "SAVE STUDENT" (§25) but doesn't confirm whether the other 4
   tabs use identical text — `save_current_tab()` takes the button name
   as a parameter rather than assuming, pending live-DOM verification.
   14 Gujarat mock scenarios (decision §4) — only New Entry + transfer-
   request-submission covered so far; Import outcome detection, session
   expiry/timeout/unknown-state/duplicate-protection scenarios remain.
7. [x] `NationalUDISEPortalAdapter` — `src/portals/udise_plus/adapter.py`:
   New PEN Entry (initialize student — verifies the exact confirmed
   success text; General/Enrolment/Facility Profile fill, label-driven
   like the Gujarat tabs; Profile Preview — verifies the exact "Data
   completion is complete." text) — spec §37-53/§164/§Y. Condition 1 is
   now feasible end-to-end against mocks/fixtures (Gujarat New Entry +
   National New PEN Entry both real, both fixture-tested). Also
   implemented the confirmed **PEN Import — Other School ACTIVE**
   workflow (DB-DESIGN.md §C.3a) in the same adapter: Aadhaar-
   availability check (`EXISTING_STUDENT_FOUND_BY_AADHAAR` business-
   routing signal, never a technical error), `View Details` →
   `Track By Details` (exact screen name preserved), Global Student
   Search by PEN, HOS Details capture. **Aadhaar consent is structurally
   never auto-clicked** — `check_aadhaar_consent_required()` only
   detects and returns, the adapter has no method that clicks "I Agree";
   proven by a dedicated integration test that toggles a fixture into
   requiring consent and asserts the page genuinely didn't advance.
   Fixture: `tests/fixtures/udise_plus/new_pen_entry.html`, tests:
   `tests/integration/test_national_udise_adapter.py` (2/2 passing, no
   selector bugs this time — applied the `exact=True` +
   `expect().to_be_visible()` lessons from step 6 from the start).
   PEN Import successful/Dropbox outcome and the remaining 32-scenario
   list (session expiry, timeout, etc.) are not yet covered.
8. [x] UDISE Import / transfer-request branch (Condition 2/4's UDISE half)
   — `run_udise_import_branch()` in `src/engine/branches.py`, fixture
   extended (`tests/fixtures/gujarat_udise/new_entry.html`: Standard Wise
   Entry search, Transfer Student page, Transfer From/To, success
   message) + 2 new integration tests
   (`tests/integration/test_gujarat_adapter.py`): other-school student
   found + transfer confirmation + `REQUEST SENT`, and no-match returns
   False rather than guessing (spec §300). Duplicate-request-protection
   and session/timeout scenarios remain open (see mock scenario
   checklist below).
9. [x] PEN Import/Other-State branch (Condition 2/3's PEN half,
   DB-DESIGN.md §C.3a) — now wired into `src/engine/branches.py`'s
   `run_pen_import_branch()` + `src/engine/audit.py`'s
   `record_pending_event()` (ACTION_REQUIRED, never RESOLVED — Final
   Authority §J). Fixture extended (`tests/fixtures/udise_plus/
   new_pen_entry.html`: Aadhaar availability check, Track By Details,
   Global Student Search, HOS Details) + 2 new integration tests. Found
   and fixed a real adapter bug this session: `get_by_label()`/
   `get_by_text()` do substring matching by default and do NOT exclude
   merely-`hidden` elements (unlike `get_by_role`, which is
   accessibility-tree-based) — "Aadhaar Number" ambiguously matched
   "Check AADHAAR Number Availability", and "PEN" matched "Student PEN";
   fixed by adding `exact=True` throughout
   `NationalUDISEPortalAdapter`'s PEN Import methods. Also rebuilt the
   National fixture around `<template>` + single-container swap (one
   screen's markup in the DOM at a time) instead of hidden-section
   toggling, since several confirmed field labels ("Student Name",
   "Student PEN") legitimately repeat across different real portal
   screens. `IMPORT PENDING` sheet-write verification covered;
   ambiguous-match/no-result/details-unavailable failure paths remain.
9a. [x] PEN Request Sent (Student Release Request generation, DB-DESIGN.md
    §C.3b) + View Sent Request (§C.3c) — `NationalUDISEPortalAdapter`:
    `get_student_release_details()` (Get Details + identity fields, spec
    step 3), `submit_release_admission_detail()` (step 4),
    `generate_release_request()` (confirmation dialog -> Confirm -> success
    message -> Request No. capture, steps 5-7), `open_sent_requests()` /
    `find_sent_request()` (confirmed column order: S.No., Request No./PEN,
    Requested By, Requested To, Closed/Auto Closed By, Request Status,
    Action) / `open_sent_request_student_details()` (student snapshot,
    spec §5) / `normalize_release_request_status()` (only "Pending at
    Destination" is a known mapping — anything else is
    `UNKNOWN_PORTAL_STATUS`, never guessed). New engine module
    `src/engine/release_request.py`: `generate_pen_release_request()`
    (verifies identity before generating — `StudentIdentityMismatchError`
    if the portal's returned name doesn't match, Final Authority §E) and
    `check_sent_request_status()` (records an `approval_checks` row,
    classifies STILL_PENDING/STATUS_CHANGED/UNKNOWN_PORTAL_STATUS — never
    auto-executes the next consequential action on a change, spec §M).
    New `src/db/request_cases.py` and `src/db/approval_checks.py`
    (schema tables already existed from step 4; nothing had written to
    them yet) plus `src/db/students.py` (`upsert_student` — needed
    because `request_cases.student_id` has a foreign key onto `students`,
    and nothing had populated that table yet either). Fixture extended
    with a persistent `#global-nav` "Student Release Request Management"
    entry point outside the per-screen `<template>` swap (it must stay
    reachable no matter which screen is currently shown — same reasoning
    as the `<template>` rebuild in step 9). 2 new integration tests
    (`tests/integration/test_release_request.py`). 39/39 tests
    project-wide.
5-9. [x] **Conditions 1-4 complete end-to-end** —
    `src/engine/condition1.py` .. `condition4.py`, refactored onto shared
    `src/engine/branches.py` (`run_udise_new_branch`,
    `run_udise_import_branch`, `run_pen_new_branch`,
    `run_pen_import_branch`), `src/engine/validation.py`
    (`validate_student`/`log_state`), `src/engine/audit.py`
    (`record_completion_event` for the OPENED->VERIFYING->RESOLVED
    pattern, `record_pending_event` for branches that end pending), and
    `src/engine/field_mapping.py` (sheet-row -> portal-field mapping; one
    assumption flagged: UDISE sheet's single "Birth City" column stands
    in for the portal's separate Taluka/Village fields, pending live-DOM
    verification), `src/engine/routing.py` (class -> ID-track). Added
    `GujaratUDISEPortalAdapter.read_generated_uid()` (spec §21).
    Condition 3 adds a UDISE-already-GREEN precondition check
    (`UdisePreconditionNotMetError` if not — spec §33.9 Case 2: a known
    UID alone is not enough). Condition 4 composes both pending-outcome
    branches (never itself directly video-demonstrated end-to-end per
    spec §11 — it's the confirmed combination of the other two). Full
    pipeline tests for all four
    (`tests/integration/test_condition{1,2,3,4}_engine.py`) match the
    decision document's acceptance diagram: Mock Sheet -> Engine -> real
    fixture-driven Gujarat + National adapters -> SQLite audit trail
    (hash-verified `pen_case_events`, correct terminal case_status per
    condition: RESOLVED for 1/3, ACTION_REQUIRED/pending for 2/4) ->
    spreadsheet verification (GREEN vs LIGHT_ORANGE, REMARK text, OGR
    color never changed by gov-entry per spec §4.4/§128.4). 37/37 tests
    project-wide.
10. [x] ND reconciliation branch (separate, explicit trigger, spec
    §165/§259-264) — `NationalUDISEPortalAdapter.search_for_nd_
    reconciliation()` (class-first, then name search; assumption flagged:
    reuses the confirmed Global Student Search screen with an invented
    "Search By Name" mode toggle mirroring the confirmed "Student PEN"
    mode — no recording separately confirms this screen's exact DOM for
    a name-based search, needs live-DOM verification). New
    `src/engine/nd_reconciliation.py`: `run_nd_reconciliation()` —
    `match_nd_candidate()` never silently picks among multiple name
    matches (narrows by DOB, else routes to manual review, spec §165.3);
    `is_actual_pen()` accepts only an 11-digit numeric value, so `NA`
    always keeps `ND` (spec §262: never invent/derive a PEN). Three
    outcomes: `PEN_FOUND` (writes PEN sheet + OGR, spec §263, and records
    a RESOLVED reopen-cycle via `src/engine/audit.py`'s new
    `record_nd_reconciliation_found_event()`), `STILL_ND` (no write, no
    event), `AMBIGUOUS_MANUAL_REVIEW` (no write, records a reopen-cycle
    ending at MANUAL_REVIEW via the new
    `record_nd_reconciliation_ambiguous_event()`). Both reopen helpers
    correctly start a NEW `case_cycle_id` on top of an already-RESOLVED
    case (DB-DESIGN.md §B.2: RESOLVED only transitions to REOPENED) while
    keeping the hash chain intact. 3 new integration tests
    (`tests/integration/test_nd_reconciliation.py`), one per outcome.
    42/42 tests project-wide.
11. [x] Approval/status-check batch flow across both portals (spec §M) +
    Status-Changed manual review queue — `GujaratUDISEPortalAdapter.
    open_transfer_request_list()`/`find_transfer_request()` (matched by
    UID — Gujarat has no separate request number, unlike National's
    Request No.; assumption flagged: exact Sent Transfer Requests column
    layout isn't spec-confirmed, needs live-DOM verification) +
    `normalize_transfer_request_status()` (only "Pending" is a known
    mapping). `run_udise_import_branch()` and `run_pen_import_branch()`
    (`src/engine/branches.py`) now also persist a `request_cases` row
    (TRANSFER_REQUEST_SENT / IMPORT_PENDING_ACTIVE) — previously nothing
    wrote to that table for these two branches, so there was nothing yet
    to batch-check. New `src/engine/approval_batch.py`:
    `check_request_case_status()` (dispatches to the correct portal by
    `request_cases.portal`) and `run_batch_status_check()` (the single
    operator-authorized confirmation covering every eligible case across
    both portals at once — spec's "ONE confirmation, not per student");
    neither ever auto-executes a next consequential action on
    STATUS_CHANGED/UNKNOWN_PORTAL_STATUS, which stay the caller's manual-
    review queue. 1 new integration test exercising both portals in one
    batch call (`tests/integration/test_approval_batch.py`). 43/43 tests
    project-wide.
12. [x] Verification gates (consequential-action rule, `MOCK_SUCCESS` vs
    `LIVE_VERIFIED_SUCCESS` distinction) wired through every branch above,
    not bolted on after — already structurally satisfied by the existing
    design rather than needing new code: every `pen_case_events`/
    `request_cases`/`approval_checks`/`diagnostics` row requires a NOT
    NULL `environment` (`MOCK`/`LIVE`) column (DB-DESIGN.md §B.4), every
    condition engine threads `self.environment` through to every event it
    records, and `GoogleSheetsRepository`'s methods all raise
    `NotImplementedError` rather than perform a real write — so a MOCK
    run is structurally incapable of producing a `LIVE_VERIFIED_SUCCESS`
    case status or a real spreadsheet write; there is no separate
    "success" enum value to wire, the environment field IS the
    distinction (spec §5).
13. [x] `AUTOMATION_PAUSED_FOR_USER` handling for CAPTCHA/OTP/Aadhaar
    consent (already done — see steps 6-7) + a generic recovery layer for
    session expiry, timeout, unknown page/state, browser crash, and
    network failure (both portals) — new `src/engine/resilience.py`:
    `run_with_recovery()` wraps each condition engine's `run()`.
    Deliberately does NOT invent portal-specific detection text for any
    of these five scenarios (none was demonstrated by any recording —
    RULEBOOK's backlog rule, spec §AH); instead classifies by the KIND of
    failure Playwright itself reports: a bare `PlaywrightTimeoutError`
    (the real, generic signature shared by session expiry/timeout/an
    unrecognized page) becomes `RecoverableAutomationError`, any other
    Playwright-level error (browser crash, network) becomes
    `BrowserOrNetworkFailureError` — both always preceded by a captured
    diagnostic (RULEBOOK §L2/§L3), never silently retried by this layer
    itself (spec §13: resume from checkpoint, never blindly repeat the
    portal action). `AutomationPausedForUser` and any already-structured
    `PortalError` pass through unchanged. All four `Condition*Engine.run()`
    methods now route through this wrapper (renamed their bodies to
    `_run_impl()`). 5 new unit tests
    (`tests/unit/test_resilience.py`). 48/48 tests project-wide.
14. [x] PySide6 GUI screens (UI-SPEC.md §B.1), wired to the engine —
    `src/app/`: `main.py` (entry point), `app_context.py` (`AppContext`:
    settings/DB/sheets repository; in MOCK mode seeds 5 clearly-labeled
    demo students spanning Conditions 1-4 + one ND case, so the app has
    something to show without Google Sheets access — never written to
    `students`/`request_cases` unless a run actually processes it),
    `theme.py` (navy+orange QSS from UI-SPEC.md §B.2), `main_window.py`
    (sidebar nav + `QStackedWidget`), `widgets.py` (status chips, stat
    tiles), `run_worker.py` (a `QThread` that opens its own SQLite
    connection — Python's sqlite3 connections aren't thread-safe to share
    — and drives the same fixture-backed adapters the integration tests
    use, in a visible/never-headless browser). All 8 required screens
    built and wired to real data (not mocked views): Batch Queue, Run &
    Progress (runs a real `Condition*Engine` in the background thread;
    the state-machine "stepper" is populated from the actual
    `pen_case_events` audit trail, not simulated), Approval Monitoring
    (runs the real `run_batch_status_check()`), Approval History (real
    `pen_case_events` query, filter, CSV/XLSX export via `openpyxl`), ND
    Reconciliation (runs the real `run_nd_reconciliation()`),
    Diagnostics, Automation Coverage (verbatim from UI-SPEC.md §B.5),
    Settings (read-only — editing credentials through the GUI is
    deliberately deferred to the Live Verification Gate). Verified
    working, not just "should work": launched the real app, drove a full
    Condition 1 run and a Condition 4 run through the actual UI (clicking
    Run, watching the background thread, confirming the resulting
    `pen_case_events`/`request_cases` rows appear correctly in Run &
    Progress / Approval History / Approval Monitoring, then ran the
    "Check all pending" batch action and watched it classify a real
    Gujarat transfer-request row as STILL_PENDING against the fixture),
    with screenshots reviewed at each step — this caught and fixed
    several real Qt layout bugs (column widths too narrow for chip text,
    row heights not accounting for chip padding) before calling it done.
    1 new smoke test (`tests/unit/test_app_smoke.py`: constructs
    `AppContext` + `MainWindow`, visits every screen, asserts no
    exception). 49/49 tests project-wide.
15. [x] UI-change resilience test pass (spec "UI CHANGE HANDLING —
    IMPLEMENTATION ACCEPTANCE TESTS", ~line 10481) — new
    `tests/fixtures/gujarat_udise/new_entry_ui_changed.html`: the full
    New Entry flow with every element id renamed, every field wrapped in
    an extra `<div>`, CTS fields reordered, and button/heading text
    changed to a semantically-equivalent casing/wording ("LOG IN" ->
    "Log in", "ADD NEW STUDENT" -> "Add new student", "SAVE STUDENT" ->
    "Save Student", "Next" -> "next", "STUDENT NEW ENTRY" -> "Student New
    Entry"). `tests/integration/test_ui_change_resilience.py` runs the
    exact same, unmodified `GujaratUDISEPortalAdapter` methods Condition 1
    uses against it end-to-end, plus a second test proving the spec's
    other half — an unrecognized state still fails safely with a
    structured `ConsequentialActionUnverifiedError`, never silently
    treated as success. Building this test found and fixed a **real**
    latent bug it was specifically designed to catch: added a shared
    `ci_exact()` helper (`src/portals/base.py`) and used it everywhere
    both adapters previously used case-SENSITIVE `exact=True` matching —
    the spec explicitly requires tolerating "minor text punctuation/
    capitalization changes", which case-sensitive exact matching did not.
    That change immediately exposed a genuine same-page text collision in
    the *original*, unmodified fixture ("Student New Entry" nav button
    vs. "STUDENT NEW ENTRY" heading, both present in the DOM
    simultaneously per the established "hidden doesn't filter get_by_text"
    lesson from step 9) that had been silently relying on case-sensitivity
    for disambiguation; fixed by scoping those two locators to
    `get_by_role("button", ...)` / `get_by_role("heading", ...)` — a more
    correct selector than plain text matching regardless of the
    capitalization question. 51/51 tests project-wide.
16. [x] Package with PyInstaller — `installer.spec` at the repo root,
    entry point `run_udify.py` (thin wrapper around
    `src.app.main.main()`). Bundles Playwright's package data (its own
    bundled PyInstaller hook covers most of it; the spec also explicitly
    `collect_data_files`s it as insurance) and the two MOCK fixture pages
    the GUI's demo dataset needs (`src/app/mock_fixtures.py` new module —
    resolves them via `sys._MEIPASS` when frozen, `tests/fixtures/`
    directly otherwise; `run_worker.py` and the two screens that
    previously computed this path themselves now share it). Deliberately
    does **not** bundle a Chromium binary — the target machine runs
    `playwright install chromium` once, same as development (would
    otherwise add several hundred MB for no benefit before Live
    Verification even runs). Verified by actually building
    (`pyinstaller installer.spec`) and launching the resulting
    `dist/UdiFy/UdiFy.exe` standalone — confirmed the GUI renders
    correctly (screenshotted) and its SQLite/diagnostics files are
    created — not just that the build step exits 0. SETUP-GUIDE.md and
    RELEASE-PLAN.md updated with the real, verified build/run steps
    (SETUP-GUIDE.md was still marked "skeleton, nothing built yet" from
    the PLANNING phase — now rewritten top to bottom to match reality).
    51/51 tests still passing (packaging touched only import paths, not
    engine/adapter logic).
17. **Stop at the Live Verification Gate** — see checklist below. Do not
    proceed to real credential configuration or controlled live
    verification without it, and do not report credentials as a blocker
    to reaching this point.

## Mock scenario checklist (master spec decision §4 — minimum required before Live Verification Gate)

**Gujarat UDISE mocks:**
- [x] New UDISE
- [x] Existing student search
- [x] Other-school student found
- [x] Transfer confirmation
- [x] Transfer Student page
- [x] Transfer From / Transfer To
- [x] "Student Transfer request saved successfully."
- [x] `REQUEST SENT`
- [x] Student Transfer Request List
- [x] Pending request
- [x] Session expiry — modeled as the same observable signature as
      "Unknown page/state" below (spec never confirms distinguishing
      text for either); a real Playwright timeout routed through
      `run_with_recovery()`, captured with a diagnostic, tested
      (`tests/integration/test_session_timeout_scenarios.py`)
- [x] Timeout — same test as above; `run_with_recovery()` classifies any
      bare `PlaywrightTimeoutError` this way
- [x] Unknown page/state — same test; see `RecoverableAutomationError`'s
      docstring in `src/engine/resilience.py` for why this and Session
      expiry/Timeout aren't distinguished (no recording confirms distinct
      text for any of them)
- [x] Duplicate-request protection — `find_open_request_case()`
      (`src/db/request_cases.py`) + a check at the top of
      `run_udise_import_branch()` (`src/engine/branches.py`): a second
      call for the same student recognizes the existing
      `TRANSFER_REQUEST_SENT` row and returns without touching the
      Gujarat portal again, tested
      (`tests/integration/test_duplicate_request_protection.py`)

**National UDISE+ mocks:**
- [x] New PEN
- [x] Successful student initialization
- [x] General Profile
- [x] Enrolment Profile
- [x] Facility Profile
- [x] "Data completion is complete."
- [x] PEN = `NA` on portal → spreadsheet PEN = `ND`
- [x] Aadhaar already registered
- [x] `View Details`
- [x] `Track By Details`
- [ ] Existing PEN discovery
- [x] Global Student Search
- [x] Student Status = `ACTIVE`
- [x] HOS Details
- [x] `IMPORT PENDING`
- [x] Student Release Request generation
- [x] Release confirmation dialog
- [x] Release request success
- [x] Request No capture
- [x] Sent Request list
- [x] `Pending at Destination`
- [x] Student Details modal
- [x] ND reconciliation — actual 11-digit PEN discovered
- [x] ND reconciliation — PEN remains unavailable
- [x] Portal status unknown — `normalize_release_request_status()` only
      maps the one confirmed wording ("Pending at Destination"); anything
      else is `UNKNOWN_PORTAL_STATUS`, which `classify_status_check()`
      always routes to manual review regardless of history, tested
      (`tests/unit/test_portal_status_normalization.py`)
- [x] Session expiry — same `run_with_recovery()` mechanism as the
      Gujarat side above, tested against the National adapter too
      (`tests/integration/test_session_timeout_scenarios.py`)
- [x] Timeout — same test
- [x] Network failure — see Browser crash below (Playwright surfaces
      both as the same generic error class)
- [x] Browser crash — a real closed browser mid-action, routed through
      `run_with_recovery()` into `BrowserOrNetworkFailureError` with a
      captured diagnostic, tested
      (`tests/integration/test_session_timeout_scenarios.py`)
- [x] Duplicate request prevention — same mechanism as the Gujarat side
      above, applied to `run_pen_import_branch()` (`IMPORT_PENDING_ACTIVE`)
      and `generate_pen_release_request()` (`RELEASE_REQUEST_SENT`), both
      tested in the same file.

## Live Verification Gate (master spec decision §8/§13 — after the mock scenario checklist above is complete)

Do not process a large student batch immediately once real credentials
are supplied. Phases, in order: **L1 Authentication** (Google Sheets,
Gujarat portal, National UDISE+ portal login — no credentials in logs) →
**L2 Read-only verification** (open correct portal, identify page/
navigation/student search, read fields/status/state — no consequential
action) → **L3 Controlled student verification** (one specifically
authorized test student: identity matching, navigation, field mapping,
selectors, state detection, confirmation handling, success detection, DB
event creation, spreadsheet verification) → **L4 Recovery verification**
(timeout, session expiry, browser restart, network interruption,
spreadsheet write failure, unknown UI state, duplicate-action
protection). Only after L1-L4 should larger-scale processing be
considered.

At the gate, report exactly this template (never claim live functionality
untested against real systems; never report credentials as a blocker to
reaching this point):

```text
MOCK IMPLEMENTATION: COMPLETE / INCOMPLETE
MOCK TESTS: PASS / FAIL
INTEGRATION TESTS: PASS / FAIL
LIVE GOOGLE SHEETS: NOT VERIFIED
LIVE GUJARAT UDISE: NOT VERIFIED
LIVE NATIONAL UDISE+: NOT VERIFIED
LIVE CREDENTIALS: NOT CONFIGURED
```

## Testing matrix (spec §286 — minimum required coverage)

- [x] New UDISE + New PEN (Condition 1)
- [x] New UDISE + PEN Import (Condition 2)
- [x] UDISE Import + New PEN (Condition 3)
- [x] UDISE Import + PEN Import (Condition 4)
- [x] New PEN resulting in `ND`
- [x] `ND` later becoming an actual PEN (reconciliation)
- [x] Already-GREEN row is skipped — **closed 2026-09-25** by
      `src/engine/entry_router.py`'s `run_entry()` (see "Correct entry-
      condition routing" in the acceptance criteria below for detail);
      tested (`test_already_complete_both_sides_green_is_skipped_not_a_condition`,
      `test_run_entry_skips_an_already_complete_student`).
- [x] Duplicate search results → manual review, not auto-pick —
      `match_nd_candidate()` / `AMBIGUOUS_MANUAL_REVIEW`, tested
      (`test_ambiguous_match_routes_to_manual_review_without_writing_sheet`)
- [x] Wrong-student search result → identity check blocks it —
      `StudentIdentityMismatchError`, tested
      (`test_generate_release_request_rejects_identity_mismatch`)
- [x] UDISE validation failure — **closed 2026-09-25**,
      `tests/unit/test_validation.py`: missing name/class_name raise
      `StudentIdentityError` before any branch runs; `run_udise_new_
      branch()` separately refuses to proceed without a UDISE sheet row,
      before any Gujarat portal action.
- [x] PEN validation failure — same file; `run_pen_new_branch()` refuses
      to proceed without a PEN sheet row, before any National portal
      action.
- [ ] Session timeout → pause + resume from checkpoint — the "pause and
      classify" half exists (`RecoverableAutomationError`,
      `tests/unit/test_resilience.py`); "resume from a persisted
      checkpoint" does not — `workflow_runs.checkpoint_json` exists in
      the schema but nothing writes or reads it yet.
- [ ] Browser crash → DB state persisted, re-verify before repeating —
      `BrowserOrNetworkFailureError` detects and diagnoses a real crash
      (tested against an actually-closed browser, not just a simulated
      exception — `tests/integration/test_session_timeout_scenarios.py`);
      "re-verify before repeating" as an actual retry flow is still not
      built.
- [ ] Save succeeded but confirmation not seen → verify state, don't
      repeat — the underlying principle (never treat an unverified
      action as success) is enforced everywhere via
      `ConsequentialActionUnverifiedError`, but there is no dedicated
      retry-without-repeating flow built on top of it yet.
- [ ] Spreadsheet update failure after portal success → recovery path,
      never repeat the portal action — `MockSheetsRepository` can
      simulate this (`simulate_write_failure`) but no engine-level
      recovery test exercises "portal already succeeded, only retry the
      sheet write" end-to-end.
- [ ] File upload failure — no file-upload functionality is implemented
      at all yet (not reached by any condition built so far).
- [ ] Dependent dropdown delay — no explicit wait-for-dependent-option
      handling beyond Playwright's own default actionability waits.
- [x] Manual consent checkpoint (Aadhaar) — structurally can never
      auto-click "I Agree", tested
      (`test_aadhaar_consent_pauses_and_is_never_auto_clicked`)
- [x] Manual review path end-to-end (open → action → resolve) —
      **closed 2026-09-25**, new `record_manual_resolution()`
      (`src/engine/audit.py`): `PEN_MANUAL_ACTION_COMPLETED` (requires an
      action description) → `PEN_RESOLVED` (requires a resolution note),
      continuing the case's existing reopen cycle rather than starting a
      new one; refuses with `CaseNotInManualReviewError` if the case
      isn't actually at `MANUAL_REVIEW`. Full open→action→resolve chain
      tested end to end starting from ND reconciliation's real ambiguous-
      match path (`tests/integration/test_manual_review_resolution.py`).
- [~] Resume after interruption — **partially closed 2026-09-25**: a
      between-branch interruption (crash/kill after the UDISE branch
      verified GREEN but before the PEN branch ran) now resumes
      correctly without repeating the completed portal action, as a
      direct consequence of `entry_router.py`'s sheet-state detection —
      re-determining the condition against the post-interruption sheet
      state naturally routes to "Condition 3" (PEN-only), tested end to
      end (`tests/integration/test_resume_after_interruption.py`).
      Resuming **mid-branch** (e.g. a crash halfway through the New PEN
      form's multiple steps) is a different, larger problem this does
      not solve — that would need the `workflow_runs.checkpoint_json`
      persistence mechanism, still unbuilt.

## Acceptance criteria (spec §287 — "fills forms" is not "done")

- [x] Correct student selection (multi-attribute identity check) —
      `validate_student()` + `StudentIdentityMismatchError`, tested
- [x] Correct class routing (Satyam School ID vs Block ID) —
      `determine_id_track()`, 9 unit tests covering every listed class
      (`tests/unit/test_routing.py`, added while auditing this checklist
      — the existing integration tests only ever exercised the BLOCK_ID
      branch, since every demo/test student uses "LKG/KG1/PP2")
- [x] Correct entry-condition routing (1-4) — **closed 2026-09-25**, new
      `src/engine/entry_router.py`: `determine_udise_state()`/
      `determine_pen_state()` read a student's actual sheet state (row
      color, known UID, Aadhaar-import signal per spec §6) into
      `NEW`/`IMPORT_PENDING`/`ALREADY_COMPLETE`, matched against spec
      §79's decision tree; `run_entry()` dispatches to the matching
      `Condition*Engine` automatically. Also closes "Already-GREEN row is
      skipped" (spec §264, immediately below) in the same place, since
      both requirements read the same sheet state — both-sides-GREEN
      returns `None` without touching either portal. Any combination the
      decision tree doesn't define (e.g. one side already GREEN, the
      other IMPORT-pending) is never guessed into the nearest condition —
      raises `AmbiguousEntryConditionError` for manual review instead. 8
      unit tests (`tests/unit/test_entry_router.py`) + 3 integration
      tests exercising real fixture-driven dispatch, the skip, and the
      ambiguous-raise (`tests/integration/test_entry_router.py`).
      `src/app/run_worker.py` (the GUI's Run & Progress screen) now calls
      `run_entry()` instead of the caller picking a condition — verified
      by actually running it through the live GUI.
- [x] Correct field mapping (no silent misalignment) —
      `field_mapping.py`, exercised end-to-end in every condition test
      (exact values asserted, not just "no exception")
- [ ] Correct dependent-dropdown handling — no distinct handling beyond
      default Playwright waits; not separately verified.
- [ ] Safe file uploads — no file-upload functionality exists yet.
- [x] Visible/headed browser operation (never headless for the government
      portal without explicit authorized exception) — every launch site
      (adapters' own tests, `run_worker.py`, both GUI batch workers)
      calls `chromium.launch(headless=False)` explicitly; watched real
      browser windows open during GUI verification.
- [x] Verified portal completion before any business-state write — the
      `_verify_visible()`/`ConsequentialActionUnverifiedError` pattern
      used by every branch, tested directly
      (`test_verification_failure_raises_rather_than_assuming_success`)
- [x] Correct GREEN behavior (whole row, only when verified) — tested in
      every Condition 1/3 integration test
- [x] OGR row-color preservation (never turns green from gov-entry) —
      explicitly asserted in `test_condition1_engine.py`
- [x] Correct `ND` semantics (success, not failure) — tested throughout
      (Condition 1/3 accept PEN=ND as `COMPLETE`; `is_actual_pen()`
      never treats `NA`/`ND` as a real PEN)
- [ ] Reliable sheet synchronization — no distinct synchronization
      mechanism beyond direct read/write calls; not separately verified.
- [ ] Retry/resume correctness — no retry/resume mechanism is built yet
      (same gap as "Session timeout"/"Resume after interruption" above).
- [x] Manual review flow works end-to-end — see the matching item above
      (closed 2026-09-25).
- [x] Logging meets RULEBOOK.md §L bar (diagnosable without asking the
      operator to describe internals) — structured JSON logging with
      session correlation, secret redaction, and `diagnostic_id`s
      throughout; 6 dedicated tests including a deliberately-triggered
      failure (`tests/unit/test_diagnostics.py`)
- [x] No credential hardcoding — every credential comes from
      `Settings`/`.env`; fixture/test values are clearly-fake literals
      ("not-a-real-password", "mock-password"), never real secrets
- [x] No fabricated data (bank `NA`, no invented PEN, etc.) —
      `is_actual_pen()` only accepts a genuine 11-digit value; bank
      fields are simply not implemented (never populated with a
      fabricated placeholder either)
- [x] No blind duplicate submissions (transfer requests, PEN init,
      etc.) — **closed 2026-09-25** for transfer/release/import
      requests: `find_open_request_case()` protects
      `run_udise_import_branch()`, `run_pen_import_branch()`, and
      `generate_pen_release_request()` (3 tests,
      `tests/integration/test_duplicate_request_protection.py`), on top
      of `MockSheetsRepository`'s existing duplicate-*write* prevention.
      New-UDISE/New-PEN *initialization* (`run_udise_new_branch`/
      `run_pen_new_branch`) has no equivalent guard yet — a second call
      would attempt a second "ADD NEW STUDENT"/"Add New Student" click;
      lower risk in practice since both are one-shot creation actions
      inside a single run, not a separately-resumable request, but not
      explicitly tested either.
- [x] `MOCK_SUCCESS` can never be written as `LIVE_VERIFIED_SUCCESS`, or
      cause a real spreadsheet write, or a claim of government completion
      (decision 2026-09-25) — see step 12's note: structurally enforced
      via the mandatory `environment` field and `GoogleSheetsRepository`
      raising `NotImplementedError` until the Live Verification Gate.

## Backlog / explicitly deferred (not invented as scope — RULEBOOK.md §J14)

- Exact UDISE Scholarship & Facility and Health & CWSN field numbering —
  live-DOM verification task, not blocking other branches.
- Numeric MVP success metrics — owner input needed (DISCOVERY.md open
  question 1).
- **Confirmed `COMING_SOON` adapter boundaries** (re-derived 2026-09-25,
  updated twice same day — see UI-SPEC.md §B.5 for the current table and
  exact spec citations): only the **successful/Dropbox outcome** of UDISE
  Import and of PEN Import (and any Condition-4 combination including
  one) remain open — build these as explicit manual-handoff adapters per
  IMPL-SPEC.md, not as ordinary automated branches, and do not attempt
  full automation without a new source recording (spec §AH). Everything
  else — UDISE Import's ACTIVE/pending outcome, PEN Import's ACTIVE/
  pending outcome, PEN Request Sent (release-request generation), and
  View Sent Request (National status monitoring) — is fully confirmed and
  belongs in the normal build order below, not the backlog. The UI's
  Automation Coverage screen is the operator-facing statement of this
  same boundary — keep both in sync if either changes.
- Any other portal behavior beyond the nine analyzed recordings — stays
  `COMING_SOON` / `MANUAL_REQUIRED` until new evidence arrives (spec §AH).

## Next trigger

**Stopped at the Live Verification Gate (2026-09-25)** — see the report
template above ("Live Verification Gate" section) for the exact status.
The mock-first build order (steps 1-16) is complete; step 17 itself
(controlled live verification) requires the user present, real
credentials configured, and explicit authorization — none of which are
in scope for this session per the mock-first decision.

Awaiting one of:
- **"run tests" / "test it"** — to formally close the TESTING gate (the
  underlying tests already pass; this trigger is about the governance
  gate, not re-running pytest).
- Real Google Sheets / Gujarat UDISE / National UDISE+ credentials, to
  begin L1-L4 controlled live verification per the phase sequence above.
- Specific follow-up work against any item left unchecked in the mock
  scenario checklist / testing matrix / acceptance criteria above (all
  explicitly and honestly marked, not silently skipped).
