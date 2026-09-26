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
| TESTING | **Passed** ("test it", 2026-09-26) — 90/90 unit+integration tests passing (full suite re-run at gate closure, not just the 51/51 recorded at step 16). Closed for everything actually built under the mock-first scope; the acceptance-criteria/testing-matrix items still `[ ]` below are unbuilt features (checkpoint/resume, retry-without-repeat flows, file upload, dependent-dropdown handling, new-entry duplicate guard), not failing tests — carried to backlog rather than silently waved through | **"run tests" / "test it"** ✅ |
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

    **Contradicted 2026-09-26 — rebuilding the same spec on the confirmed
    target machine, the resulting `.exe` would not launch at all**:
    `Start-Process` (and a direct double-click via a Start Menu shortcut)
    failed with "An Application Control policy has blocked this file" —
    a Windows security policy on this machine blocks unsigned/unknown
    executables, which a freshly PyInstaller-built binary always is
    without a code-signing certificate (out of scope, real cost/process).
    `.venv\Scripts\pythonw.exe run_udify.py` (running from source,
    windowless) launches the identical app successfully — `pythonw.exe`
    is an already-trusted binary the policy allows. A Start Menu shortcut
    (`UdiFy.lnk`) now launches the app this way instead. This means the
    packaged-`.exe` distribution path this step believed it had verified
    does not actually work here — either the policy was added/tightened
    between the two sessions, or the school's actual machine was never
    what step 16 built against. RELEASE-PLAN.md's "Build"/"Deployment
    steps" sections updated to record the real, working path.
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
- [x] Existing PEN discovery — this is `Track By Details`'s own purpose
      (discovering the PEN an existing-elsewhere student already has,
      spec step 8): `TrackByDetailsResult.student_pen`, asserted directly
      in `test_pen_import_other_school_active_flow_against_fixture`. Not
      a separate mechanism from the line above — re-audited and checked
      off under its own name for a literal reading of the master spec's
      minimum-coverage list.
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

### L1 Authentication — started 2026-09-26

**Status, honestly, as of this writing:**

```text
MOCK IMPLEMENTATION: COMPLETE
MOCK TESTS: PASS (110/110)
INTEGRATION TESTS: PASS
LIVE GOOGLE SHEETS: VERIFIED (read-only connectivity — real find/get
  read/write methods on GoogleSheetsRepository are still
  NotImplementedError, deliberately not built yet — see below)
LIVE GUJARAT UDISE: VERIFIED (login only)
LIVE NATIONAL UDISE+: VERIFIED (login only)
LIVE CREDENTIALS: CONFIGURED
```

**Google Sheets**: the 3 real spreadsheets were discovered to be
uploaded `.xlsx` files in Office-compatibility mode, not native Google
Sheets — the Sheets API can't operate on them as-is (`400: This
operation is not supported for this document`). Converting via the
Drive API (`files.copy` to a Sheets mimeType) hit a separate hard wall:
**service accounts have zero Drive storage quota of their own**, so they
cannot create new files at all, even copies. The user converted each
file themselves in the Sheets UI (their own account/quota), producing 3
new native-Sheets files; the service account was re-shared with each,
`.env` updated to the new IDs. A read-only connectivity check (`spread-
sheets().get()` on all 3, via a throwaway script — not part of the app)
confirmed authentication and read access, with tab names matching the
codebase's expectations exactly (PH1/PH2/PH3, IMPORT PENDING, PRIMARY/
GENERAL). `GoogleSheetsRepository`'s actual find/read/write methods
remain `NotImplementedError` — L1 only proves connectivity, not that
those methods are built; that's L2/L3 work, not yet started.

**Government portal logins**: real, first-ever contact with both
portals surfaced genuine bugs neither mock fixture could have caught
(both fixed, each confirmed by re-running against the live portal until
it worked, not just by reasoning about the code):
- Both real portals have a password-visibility toggle button whose
  accessible name ambiguously substring-matched the password field's
  own label — fixed via `input[type="password"]` (the field's real
  semantic type) instead of label matching.
- Both real portals have a captcha; Gujarat's entry field isn't labeled
  "Captcha" (that's a section heading) — its real placeholder is "ENTER
  CODE". National's "Captcha" `<label>` has no `for` attribute at all —
  found by dumping every real `<input>`/`<label>` element, not guessing;
  the real field is `input[name="captcha"]`.
- Both captcha checks originally only checked the field's *visibility*,
  which stays true whether or not the operator has typed the code — so
  a solved captcha still read as "still blocking". Fixed to check the
  field's *value* instead (empty = waiting on the operator; non-empty =
  proceed — this adapter still can never judge whether a code is
  *correct*, only the real portal can, on submission).
- National UDISE+'s real submit button reads "Sign In", not "Login" (the
  mock fixture's button text was apparently never checked against the
  real portal) — now accepts either, so the mock fixture keeps working.

All five fixes are in `src/portals/base.py` / `udise_gujarat/adapter.py`
/ `udise_plus/adapter.py`, each with its own commit, each still passing
110/110 tests (none of these paths were ever exercised by a mock
fixture, so there was no regression risk in fixing them — but also no
automated coverage for them beyond this manual live confirmation).

**Not yet done**: L2 (read-only navigation/search on both real portals),
L3 (one controlled test student, full real run), L4 (recovery
scenarios). `GoogleSheetsRepository`'s read/write methods are now built
— see "L2 Read-only (Sheets half)" below. Do not treat L1 passing as
license to process real students — per spec, L2/L3/L4 come first, in
order, and the two real portals still have no L2 done.

### L2 Read-only (Sheets half) — 2026-09-27

`GoogleSheetsRepository`'s `NotImplementedError` stubs are replaced with
real implementations (`get_row_values`, `get_row_color`, `write_cell`,
`set_row_color`, `verify_cell`, `find_by_name`, `find_by_uid`,
`find_by_pen`) — full detail and design rationale in the class's
docstrings/comments, `src/sheets/repository.py`. Read methods verified
against the real live sheets (read-only scratch script, not part of the
app or committed):

- `get_row_values` on a real row of each of the 3 sheets decoded every
  column correctly — headers read from the sheet's own row 1, not
  hardcoded, so a header reorder/rename doesn't silently break this.
- `get_row_color` on untouched real rows correctly returned `UNCHANGED`
  (no background color set yet in any of the 3 sample rows checked).
- `find_by_name` against the real OGR tabs found the expected row.
- **New finding, not previously in DB-DESIGN.md**: the live OGR sheet
  has **17** columns, not the documented 16 — an extra `REMARK` column
  at the end (`AY, NAME, STD, MOBILE 1, MOBILE 2, PR, T-GR, TC, DOB, DOA,
  DOE, AADHAR, UID, PEN, APAAR, DOCUMENTS PENDING, REMARK`). DB-DESIGN.md
  §A.1 updated to match. Nothing in the codebase currently writes to
  or reads `REMARK` on OGR — just recording the header list is
  accurate now that it's been read for real.
- `write_cell`/`set_row_color` (the two write paths) are implemented but
  **not yet exercised against a real sheet** — deliberately: writing to
  the real production OGR/UDISE/PEN sheets needs one specifically
  authorized test student (L3), not a throwaway smoke-test row. Column-
  layout-dependent code (`write_cell` looks up the target column by
  reading the tab's real header row) exercised the read half of that
  same code path already, above.
- Assumption flagged, not yet confirmed: `find_by_name`/`find_by_uid`/
  `find_by_pen` build each `Student.student_id` from OGR's `AADHAR`
  column (`"aadhar:<value>"`) since nothing in any of the 3 sheets is a
  ready-made internal case key, and this ID must stay stable for a given
  student across every app run (it indexes the local, append-only
  `pen_case_events` table). A row with no Aadhaar on file falls back to
  a row-position key instead, which is unstable if that row is later
  reordered — logged as a warning when it happens; not yet hit against
  real data, since the one live row checked did have an Aadhaar. None of
  these 3 methods are called by any engine code yet (confirmed by grep),
  so this doesn't block anything today, but should be revisited before
  any future feature relies on it.

**Not yet done**: L2 on the two government portals (read-only
navigation/search), and exercising the two write paths above against a
real sheet.

### L3 attempt #1 (PRIYANSHI PADUKA PRADHAN) — 2026-09-27, blocked before any write

User explicitly authorized a real, live Condition 1 run (New UDISE + New
PEN) for a specific real student — UDISE_Entry_(State)/PH2 row 10,
PEN_Entry_(National)/PH2 row 10, Aadhaar 572345294349, class Balvatika,
UDISE No and PEN both still empty/unset at the time. This was run via a
controlled script (`Condition1Engine` unchanged, real sheets, real
portal adapters — same pattern as the L1 login test), not yet through
the GUI (`src/app/run_worker.py` is still hardcoded to MOCK mode only —
no live-mode path exists there yet, separately noted, not built this
session).

**Result: no write happened, nothing was submitted.** The run correctly
stopped itself early with `RecoverableAutomationError` (a genuine
Playwright timeout — "Portal did not reach the expected state in
time") rather than doing anything to the real portals or sheets. Two
real, previously-unknown bugs were found and fixed as a direct result of
this attempt:

1. **`NationalUDISEPortalAdapter.login()` had no success verification at
   all** — it filled the fields, clicked Sign In, and returned
   unconditionally, so a *wrong* captcha (confirmed live: the real
   portal shows an "Invalid Captcha" toast and stays on the login page)
   silently reported as a successful login. Fixed: `login()` now calls
   `_verify_login_succeeded()`, which waits for the "Welcome `<name>`,"
   text confirmed on the real post-login dashboard
   (`src/portals/udise_plus/adapter.py`). The mock fixture
   (`tests/fixtures/udise_plus/new_pen_entry.html`) got a matching
   `Welcome Mock User,` marker on its own post-login screen so the same
   check works for both — same pattern as the Gujarat mock's `Home`
   span. All 110 tests still pass (107 passed / 3 skipped) with this
   change.
2. **`initialize_new_student()`'s navigation assumption doesn't match
   the real portal.** It assumes "Add New Student" is directly reachable
   right after login (matching the mock, which jumps straight there).
   Real evidence (live, read-only exploration, 2026-09-27) says
   otherwise — the real post-login flow is:
   `Login` → **dashboard hub** (`https://sdms.udiseplus.gov.in/one-view/dashboard`,
   "Welcome `<name>`," 4 module cards: School Directory, School Profile
   & Facilities, Teacher Module, Students Module, each with its own "Go"
   button) → clicking **Students Module's "Go" opens a NEW browser
   tab/window** (`https://sdms.udiseplus.gov.in/g2/#/academic-choice`,
   "UDISE+ Student Module") → an **academic-year-choice screen**
   ("Current Academic Year 2026-27" / "Snapshot 2025-26", pick one) →
   **not yet explored beyond this point** — where "Add New Student"
   actually lives is still unconfirmed. `initialize_new_student()` is
   **not fixed yet** — flagging this rather than guessing further
   navigation without evidence (RULEBOOK K1). Against the real portal
   today it will correctly fail (Playwright timeout →
   `RecoverableAutomationError`, the exact failure this L3 attempt hit)
   rather than silently doing something wrong — a safe failure mode,
   just not yet a working one.

Two more real findings from the same exploration, both worth keeping in
mind for later work, neither acted on yet:

- The dashboard's "Activity Permissions" panel states **"Add Student
  (PP3 to Class 1) is allowed"** for the current academic year — a
  real, live eligibility restriction on new-student creation not
  documented anywhere before this. User confirmed Balvatika (Priyanshi's
  class) falls within this "PP3 to Class 1" range, so this doesn't block
  her specifically, but this constraint is real and could block other
  classes — nothing in the codebase currently checks it before
  attempting a New UDISE/PEN entry.
- The same panel states **"Send to Dropbox is not permitted"** —
  confirms, independently of docs, why `run_udise_import_branch`'s
  successful/Dropbox outcome is deliberately left unimplemented
  (DB-DESIGN.md's own note on this already said not to guess this path).

**Not yet done, revised**: mapping the real navigation from the
academic-year-choice screen to an actual "Add New Student" screen (more
live exploration needed before `initialize_new_student()` can be
trusted against the real portal), L2 on both government portals more
generally, L3 attempt #2 once that navigation is fixed, L4.

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
- [~] Session timeout → pause + resume from checkpoint — **partially
      closed 2026-09-26**: the "pause and classify" half already existed
      (`RecoverableAutomationError`, `tests/unit/test_resilience.py`);
      persisting a checkpoint now also exists — new `src/db/
      workflow_runs.py` (`start_run`/`patch_checkpoint`/`complete_run`/
      `find_incomplete_run_with_checkpoint_flag`), wired into
      `run_with_recovery()` (every condition-engine run gets a
      `workflow_runs` row, left incomplete on any exception path) and
      into the New UDISE/New PEN branches (checkpointed mid-branch
      progress — `udise_new_uid`, `pen_new_initialized`, etc.). What's
      still missing: genuinely resuming a *portal session* mid-timeout
      (re-logging in and picking back up where the timeout occurred) —
      only the New UDISE branch can resume past a checkpoint today (see
      "No blind duplicate submissions" below), and only because the next
      step it needs (`open_student_profile`) is an already-confirmed,
      unconditionally-run adapter method, not new navigation.
- [x] Browser crash → DB state persisted, re-verify before repeating —
      **closed 2026-09-26**. `BrowserOrNetworkFailureError` already
      detected and diagnosed a real crash (tested against an actually-
      closed browser — `tests/integration/test_session_timeout_
      scenarios.py`); "DB state persisted" is now literally true (the
      `workflow_runs` row from the interrupted run stays queryable and
      incomplete, `tests/unit/test_workflow_runs.py`), and "re-verify
      before repeating" is enforced for the two one-shot creation actions
      that used to have no guard at all: `run_udise_new_branch`/
      `run_pen_new_branch` now check for a prior interrupted attempt
      before clicking "ADD NEW STUDENT"/"Add New Student" again
      (`tests/integration/test_new_entry_duplicate_guard.py`) — never
      blindly repeating a one-shot portal-creation click, per spec's "no
      blind duplicate submissions" (see the acceptance-criteria item
      below, now fully closed).
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
- [ ] File upload failure — still no file-upload functionality wired into
      any condition (not reached by any confirmed screen so far).
      **2026-09-26**: added generic, portal-agnostic helpers
      (`src/portals/base.py`: `set_file_input()`) tested in isolation
      against a synthetic fixture (`tests/integration/
      test_generic_portal_helpers.py`) — deliberately NOT wired into any
      adapter or branch, since no recording confirms a file-upload screen
      on either portal (RULEBOOK §J14: no invented selectors). Ready to
      plug in once one is confirmed.
- [ ] Dependent dropdown delay — still no distinct handling wired into
      any condition; Playwright's default actionability waits have
      covered every fixture tested so far. **2026-09-26**: same treatment
      as file upload above — a generic `wait_for_dependent_option()`
      helper exists and is tested (`tests/integration/
      test_generic_portal_helpers.py`), unwired pending a confirmed
      screen.
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
- [~] Resume after interruption — **partially closed 2026-09-25, extended
      2026-09-26**: a between-branch interruption (crash/kill after the
      UDISE branch verified GREEN but before the PEN branch ran) resumes
      correctly without repeating the completed portal action, as a
      direct consequence of `entry_router.py`'s sheet-state detection —
      re-determining the condition against the post-interruption sheet
      state naturally routes to "Condition 3" (PEN-only), tested end to
      end (`tests/integration/test_resume_after_interruption.py`).
      **2026-09-26**: mid-branch resume is now solved for the one case
      where it's safe without inventing portal navigation — a crash
      *inside* `run_udise_new_branch` after the UID was obtained but
      before the sheet write resumes using the checkpointed UID rather
      than re-clicking "ADD NEW STUDENT"
      (`test_udise_new_branch_resumes_using_checkpointed_uid_without_
      reclicking_add_new_student`). Mid-branch resume for `run_pen_new_
      branch` (a crash partway through the multi-tab profile fill) is
      still not solved — no recording confirms a way to reopen an
      in-progress National UDISE+ PEN entry, so that case detects the
      interruption and routes to manual review rather than guessing
      (`test_pen_new_branch_raises_on_prior_interrupted_attempt_never_
      reinitializes`), which is the honest boundary of what's
      automatable without new evidence (spec §AH).

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
- [ ] Correct dependent-dropdown handling — no distinct handling wired
      into any condition beyond default Playwright waits; not separately
      verified against a real portal screen. **2026-09-26**: a generic,
      tested `wait_for_dependent_option()` helper now exists
      (`src/portals/base.py`) but is deliberately unwired — see the
      matching testing-matrix item above for why.
- [ ] Safe file uploads — no file-upload functionality is wired into any
      condition. **2026-09-26**: same treatment — a generic, tested
      `set_file_input()` helper exists (`src/portals/base.py`), unwired
      pending a confirmed screen.
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
- [~] Retry/resume correctness — **partially closed 2026-09-26**: see
      "Session timeout"/"Resume after interruption" above — the New
      UDISE branch now genuinely resumes past a checkpoint, and both New
      UDISE/New PEN branches detect an interrupted prior attempt before
      retrying. The three still-open testing-matrix retry gaps (save-
      succeeded-unconfirmed, sheet-write-failure-after-portal-success,
      full mid-branch resume for the National UDISE+ multi-tab profile
      fill) remain unbuilt.
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
      **Extended 2026-09-26** to New-UDISE/New-PEN *initialization*: new
      `src/db/workflow_runs.py` (`find_incomplete_run_with_checkpoint_
      flag`) lets `run_udise_new_branch()`/`run_pen_new_branch()` detect
      a previous interrupted attempt before clicking "ADD NEW STUDENT"/
      "Add New Student" again. UDISE resumes using the checkpointed UID
      when one was already obtained; PEN always raises for manual review
      (no confirmed way to reopen an in-progress PEN entry) — neither
      ever blindly re-clicks the one-shot creation button. 3 tests
      (`tests/integration/test_new_entry_duplicate_guard.py`).
- [x] `MOCK_SUCCESS` can never be written as `LIVE_VERIFIED_SUCCESS`, or
      cause a real spreadsheet write, or a claim of government completion
      (decision 2026-09-25) — see step 12's note: structurally enforced
      via the mandatory `environment` field and `GoogleSheetsRepository`
      raising `NotImplementedError` until the Live Verification Gate.

## Backlog / explicitly deferred (not invented as scope — RULEBOOK.md §J14)

- Exact UDISE Scholarship & Facility and Health & CWSN field numbering —
  live-DOM verification task, not blocking other branches.
- ~~Numeric MVP success metrics~~ — **answered 2026-09-26**, see
  DISCOVERY.md's "Success metrics" section (no longer backlog).
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

## RELEASE gate remediation (2026-09-26)

"approve release" was said, but `RELEASE-PLAN.md`'s own release-criteria
checklist had 5 real unmet items — not marked approved outright.
User decision: resolve what's resolvable now, in code, before recording
approval; the school-dependent items get answered/arranged separately.

1. "All TESTING-phase acceptance criteria pass with evidence" —
   **materially strengthened, not fully closed**: closed the New-UDISE/
   New-PEN no-blind-duplicate-submission gap and added real checkpoint/
   resume for the UDISE branch (workflow_runs, see the testing-matrix and
   acceptance-criteria updates above, 12 new tests, 102/102 project-wide).
   Explicitly declined to build file-upload/dependent-dropdown handling
   into any real branch (no recording confirms either screen — would
   have meant inventing selectors, RULEBOOK §J14) — added generic, tested,
   unwired helpers instead. Three testing-matrix items remain genuinely
   unbuilt: save-succeeded-but-unconfirmed retry, sheet-write-failure-
   after-portal-success recovery, and full mid-branch resume for the
   National UDISE+ multi-tab profile fill.
2. SECURITY-THREAT-MODEL.md open questions — **closed 2026-09-26**: data
   retention (kept indefinitely, no school policy), encryption at rest
   (not required, OS-level protection is sufficient), Aadhaar-consent-
   always-manual (confirmed, no exceptions), and no-secrets-in-git-
   history (verified — only `.env.example` was ever added, `.env`/
   `credentials/` both confirmed git-ignored).
3. Smoke tests on the actual target machine — **closed 2026-09-26**: user
   confirmed this project's machine IS the school's actual UDISE-
   operations machine (RELEASE-PLAN.md "Environments"), so there is no
   separate target machine to additionally verify against. Re-ran the
   MOCK smoke tests through the real GUI entry point (`src/app/main.py`'s
   own theme + `AppContext` + `MainWindow` wiring, not a bypassed
   construction) on it: Batch Queue rendered correctly themed with the
   5-student MOCK dataset, a full Condition 1 run driven by actually
   clicking "Start run" completed to `RESOLVED`/GREEN/GREEN/`ND` with a
   real visible Playwright browser, all screenshotted. See RELEASE-
   PLAN.md's "Smoke tests" section for exactly what was re-verified live
   vs. already covered by the automated suite running on this same
   machine (Aadhaar-pause and diagnostics-capture-on-failure — both
   covered by existing automated tests, not re-demonstrated through the
   GUI this pass, since neither the MOCK dataset nor this run naturally
   exercises them without changing app code to force a demo scenario).
4. Rollback path — **closed 2026-09-26**, see RELEASE-PLAN.md's new
   "Rollback path" section.
5. DISCOVERY.md open question #2 (Google Cloud project/service-account
   provisioning) — **closed 2026-09-26**: checked directly via
   console.cloud.google.com — a project already existed
   (`satyam-school-play-publish`, previously used for Google Play
   Console publishing, unrelated to this project). Enabled the Sheets
   API on it and created a new, dedicated `udify-sheets-access` service
   account (not reusing the existing `play-publisher` one, to keep
   least-privilege — SECURITY-THREAT-MODEL.md). Its JSON key was
   downloaded and imported into `credentials/service-account.json`,
   `GOOGLE_SERVICE_ACCOUNT_FILE` set in `.env`. **Fully resolved same
   day**: identified the real OGR/UDISE/PEN spreadsheets by their actual
   URLs (user-supplied — Drive search alone had turned up several
   similarly-named UDISE candidates and no obvious "OGR" filename; its
   real title is "ONLINE GENERAL REGISTER", the acronym's source),
   content-verified each against field_mapping.py's expected columns/tab
   names before sharing, shared all three with `udify-sheets-
   access@satyam-school-play-publish.iam.gserviceaccount.com` (Editor),
   and recorded their 3 spreadsheet IDs in `.env`. Only the two portal
   logins (Gujarat UDISE, National UDISE+) remain to configure via
   Settings before LIVE mode is fully set up.

Remaining before "approve release" can be honestly recorded: item 1's
three still-unbuilt testing-matrix gaps (or an explicit decision to
release without them). Numeric success metrics and GCP provisioning are
both now answered/resolved — see DISCOVERY.md and BOOTSTRAP.md's "Open
questions" for the consolidated record.

## Editable Settings screen for LIVE credentials (2026-09-26)

User request (ahead of Live Verification): configure the Google Sheets
connection and both portal logins through the app instead of
hand-editing `.env` every time — "make this dynamic for any sheet"
clarified to mean *which* spreadsheet ID each of the fixed OGR/UDISE/PEN
roles points to, not an arbitrary/unknown sheet-column rebuild (that
would need re-deriving field mapping with no spec evidence — explicitly
declined, same reasoning as file-upload/dependent-dropdown above).

- New `src/config/settings_writer.py`: `write_env_values()` (updates/adds
  keys in `.env`, preserves comments and unrelated lines, never logs
  values) and `import_service_account_file()` (copies a chosen key into
  git-ignored `credentials/service-account.json`).
- `src/app/screens/settings_view.py` rewritten from read-only labels to
  an editable form: service-account key (Browse… → copies into
  `credentials/`), 3 spreadsheet IDs, Gujarat school code/username/
  password, National username/password, all behind a Save button.
  `UDIFY_ENVIRONMENT` itself stays read-only here deliberately —
  flipping into LIVE mode is kept a separate, manual `.env` edit, never
  a side effect of saving this form. A blank password field on Save
  keeps whatever was already saved rather than clearing it. Saving
  writes to `.env`/`credentials/` and takes effect on next restart —
  no hot-swap of the running session's settings.
- 8 new tests (`tests/unit/test_settings_writer.py`,
  `tests/unit/test_settings_screen.py` — the latter drives the actual
  widget: types into fields, clicks Save, asserts `.env` contents).
  110/110 project-wide. Visually verified on the target machine
  (screenshotted, navy/orange theme correct, all fields render and
  accept input).
- SETUP-GUIDE.md's "Configure" section updated with the GUI path
  alongside the existing by-hand `.env` instructions.

## Next trigger

**TESTING gate closed ("test it", 2026-09-26).** 110/110 tests passing.
RELEASE-gate remediation items are all resolved (see that section above)
— **awaiting the explicit "approve release" trigger phrase again**,
never silently assumed just because the blocking items cleared.

**Live Verification Gate**: `UDIFY_ENVIRONMENT=LIVE` (user's explicit
direction, "come real mode", 2026-09-26), real credentials configured,
**L1 Authentication passed** for Google Sheets (read-only) and both
government portals (login) — see "L1 Authentication" above for the full,
honest account including 5 real adapter bugs found and fixed live. This
proceeded independently of the RELEASE gate, consistent with this
project's own recorded plan (BOOTSTRAP.md).

Awaiting one of:
- **"approve release"** — all remediation items are resolved; this is
  now just the trigger phrase itself.
- Direction to continue Live Verification: **L2** (read-only navigation/
  search on both real portals — no writes), building
  `GoogleSheetsRepository`'s actual read/write methods (still
  `NotImplementedError`, needed before L2/L3 can do anything beyond
  connectivity), or **L3** (one controlled real test student).
- Specific follow-up work against any item left unchecked in the mock
  scenario checklist / testing matrix / acceptance criteria above (all
  explicitly and honestly marked, not silently skipped).
