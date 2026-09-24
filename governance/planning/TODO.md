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
| CODING | **In progress** — mock-first build order below | **"code it"** ✅ |
| TESTING | Not started | **"run tests" / "test it"** |
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
6. `GujaratUDISEPortalAdapter` interface + mocked pages covering the 14
   Gujarat scenarios (master spec decision §4) — UDISE New-entry branch
   (Condition 1's UDISE half).
7. `NationalUDISEPortalAdapter` interface + mocked pages covering the New
   PEN scenarios among the 32 National scenarios (master spec decision
   §4) — Condition 1's PEN half, completing Condition 1 end-to-end
   against mocks.
8. UDISE Import / transfer-request branch (Condition 2/4's UDISE half) —
   mocked scenarios: other-school student found, transfer confirmation,
   `REQUEST SENT`, pending request, duplicate-request protection.
9. PEN Import/Other-State branch (Condition 2/3's PEN half, DB-DESIGN.md
   §C.3a) — mocked scenarios: Aadhaar already registered, `View Details`,
   `Track By Details`, Global Student Search, Student Status = `ACTIVE`,
   HOS Details, `IMPORT PENDING`.
9a. PEN Request Sent (Student Release Request generation, DB-DESIGN.md
    §C.3b) + View Sent Request (§C.3c) — mocked scenarios: release
    confirmation dialog, Request No capture, `Pending at Destination`,
    Student Details modal.
10. ND reconciliation branch (separate, explicit trigger) — mocked
    scenarios: actual PEN discovered, PEN remains unavailable.
11. Approval/status-check batch flow across both portals + Status-Changed
    manual review queue.
12. Verification gates (consequential-action rule, `MOCK_SUCCESS` vs
    `LIVE_VERIFIED_SUCCESS` distinction) wired through every branch above,
    not bolted on after.
13. `AUTOMATION_PAUSED_FOR_USER` handling for CAPTCHA/OTP/Aadhaar consent
    — mocked scenarios: session expiry, timeout, unknown page/state,
    browser crash, network failure (both portals).
14. PySide6 GUI screens (UI-SPEC.md §B.1), wired to the engine.
15. UI-change resilience test pass (spec §10464-10483) before any batch
    scaling — selector fallback tests against deliberately altered mocked
    pages.
16. Package with PyInstaller.
17. **Stop at the Live Verification Gate** — see checklist below. Do not
    proceed to real credential configuration or controlled live
    verification without it, and do not report credentials as a blocker
    to reaching this point.

## Mock scenario checklist (master spec decision §4 — minimum required before Live Verification Gate)

**Gujarat UDISE mocks:**
- [ ] New UDISE
- [ ] Existing student search
- [ ] Other-school student found
- [ ] Transfer confirmation
- [ ] Transfer Student page
- [ ] Transfer From / Transfer To
- [ ] "Student Transfer request saved successfully."
- [ ] `REQUEST SENT`
- [ ] Student Transfer Request List
- [ ] Pending request
- [ ] Session expiry
- [ ] Timeout
- [ ] Unknown page/state
- [ ] Duplicate-request protection

**National UDISE+ mocks:**
- [ ] New PEN
- [ ] Successful student initialization
- [ ] General Profile
- [ ] Enrolment Profile
- [ ] Facility Profile
- [ ] "Data completion is complete."
- [ ] PEN = `NA` on portal → spreadsheet PEN = `ND`
- [ ] Aadhaar already registered
- [ ] `View Details`
- [ ] `Track By Details`
- [ ] Existing PEN discovery
- [ ] Global Student Search
- [ ] Student Status = `ACTIVE`
- [ ] HOS Details
- [ ] `IMPORT PENDING`
- [ ] Student Release Request generation
- [ ] Release confirmation dialog
- [ ] Release request success
- [ ] Request No capture
- [ ] Sent Request list
- [ ] `Pending at Destination`
- [ ] Student Details modal
- [ ] ND reconciliation — actual 11-digit PEN discovered
- [ ] ND reconciliation — PEN remains unavailable
- [ ] Portal status unknown
- [ ] Session expiry
- [ ] Timeout
- [ ] Network failure
- [ ] Browser crash
- [ ] Duplicate request prevention

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

- [ ] New UDISE + New PEN (Condition 1)
- [ ] New UDISE + PEN Import (Condition 2)
- [ ] UDISE Import + New PEN (Condition 3)
- [ ] UDISE Import + PEN Import (Condition 4)
- [ ] New PEN resulting in `ND`
- [ ] `ND` later becoming an actual PEN (reconciliation)
- [ ] Already-GREEN row is skipped
- [ ] Duplicate search results → manual review, not auto-pick
- [ ] Wrong-student search result → identity check blocks it
- [ ] UDISE validation failure
- [ ] PEN validation failure
- [ ] Session timeout → pause + resume from checkpoint
- [ ] Browser crash → DB state persisted, re-verify before repeating
- [ ] Save succeeded but confirmation not seen → verify state, don't repeat
- [ ] Spreadsheet update failure after portal success → recovery path,
      never repeat the portal action
- [ ] File upload failure
- [ ] Dependent dropdown delay
- [ ] Manual consent checkpoint (Aadhaar)
- [ ] Manual review path end-to-end (open → action → resolve)
- [ ] Resume after interruption

## Acceptance criteria (spec §287 — "fills forms" is not "done")

- [ ] Correct student selection (multi-attribute identity check)
- [ ] Correct class routing (Satyam School ID vs Block ID)
- [ ] Correct entry-condition routing (1-4)
- [ ] Correct field mapping (no silent misalignment)
- [ ] Correct dependent-dropdown handling
- [ ] Safe file uploads
- [ ] Visible/headed browser operation (never headless for the government
      portal without explicit authorized exception)
- [ ] Verified portal completion before any business-state write
- [ ] Correct GREEN behavior (whole row, only when verified)
- [ ] OGR row-color preservation (never turns green from gov-entry)
- [ ] Correct `ND` semantics (success, not failure)
- [ ] Reliable sheet synchronization
- [ ] Retry/resume correctness
- [ ] Manual review flow works end-to-end
- [ ] Logging meets RULEBOOK.md §L bar (diagnosable without asking the
      operator to describe internals)
- [ ] No credential hardcoding
- [ ] No fabricated data (bank `NA`, no invented PEN, etc.)
- [ ] No blind duplicate submissions (transfer requests, PEN init, etc.)
- [ ] `MOCK_SUCCESS` can never be written as `LIVE_VERIFIED_SUCCESS`, or
      cause a real spreadsheet write, or a claim of government completion
      (decision 2026-09-25)

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

PLANNING is approved. Awaiting **"approve design"** to close DESIGN FIXED,
or specific edit requests against DB-DESIGN.md / IMPL-SPEC.md /
SECURITY-THREAT-MODEL.md first.
