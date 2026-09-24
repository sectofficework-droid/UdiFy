# IMPL-SPEC.md — UdiFy

> Per RULEBOOK.md §E.3. This file makes coding mechanical by pointing each
> module (from PLAN.md's file map) at its exact spec sections, plus the
> conventions that apply across all of them. It does not restate the full
> field-by-field portal prose — that lives in UI-SPEC.md and the master
> spec, cited by section.

## Development sequencing: mock-first (decision 2026-09-25)

> Full authoritative detail: master spec, "UDIFY — CREDENTIALS, MOCKING
> AND LIVE VERIFICATION DECISION." Summarized here as a cross-cutting
> implementation rule, not repeated in full.

Real Google Sheets and government-portal credentials are **not** a
prerequisite for implementation. Build and fully test against mocks
first; real credentials are configured later for a separate, controlled
live-verification phase. This changes *how* every module below is built,
so it applies before the per-module mapping:

- **Every external dependency is accessed through an interface, never a
  concrete SDK/class directly.** `src/sheets/`: business logic depends on
  a `StudentSheetRepository` interface, with `GoogleSheetsRepository` and
  `MockSheetsRepository` as interchangeable implementations — the
  workflow engine must run completely against the mock. `src/portals/`:
  `GujaratUDISEPortalAdapter` and `NationalUDISEPortalAdapter` stay
  separate classes (never merged into one browser-automation class) and
  are built first against mocked/fixture pages covering every scenario
  listed in the master spec's decision section 4 (14 Gujarat scenarios,
  32 National scenarios — session expiry, timeout, duplicate-request
  protection, and every documented success/pending state among them).
- **`environment = MOCK | LIVE` is tracked as data, not assumed from
  context.** Every `pen_case_events` row and workflow-run record carries
  this field (DB-DESIGN.md §B.1/§B.4). A mock test result must never be
  capable of causing a real spreadsheet write or a claim of government
  success — `MOCK_SUCCESS` and `LIVE_VERIFIED_SUCCESS` are distinct,
  never conflated.
- **`AUTOMATION_PAUSED_FOR_USER`** is the explicit state for CAPTCHA,
  OTP, and Aadhaar-consent interruptions (unifies the existing manual-
  intervention rules below with the mock/live sequencing — this state
  exists identically in both environments).
- **Build order**: complete architecture → Sheets adapter interface +
  mock → Gujarat adapter interface + mocked pages → National adapter
  interface + mocked pages → deterministic workflow/state-machine/
  idempotency/recovery/selector-fallback/spreadsheet-verification/audit/
  approval-history/request-monitoring/ND-reconciliation tests → UI tests
  → packaging. Then **stop at the LIVE VERIFICATION GATE** (master spec
  decision §8: phases L1 Authentication → L2 Read-only verification → L3
  Controlled student verification → L4 Recovery verification) and report
  status using the exact template in the master spec's decision §13 —
  never claim live functionality untested against the real systems, and
  never report credentials as a blocker to *starting* development.

## Cross-cutting conventions (apply to every module)

- **Never guess.** Any government-portal behavior not evidenced by the nine
  source recordings must be implemented as an explicit adapter boundary
  marked `COMING_SOON` or `MANUAL_REQUIRED` (spec §AH). Label every
  source-derived fact vs. engineering-design decision distinctly in code
  comments/docstrings where it affects future maintenance (spec §AI.26,
  §191). **Confirmed `COMING_SOON` boundaries** (re-derived 2026-09-25,
  updated same day once the user supplied the PEN Import ACTIVE workflow —
  see UI-SPEC.md §B.5 for the current table and citations): the
  **successful/Dropbox outcome** of UDISE Import and of PEN Import, and
  any Condition-4 combination that includes one, remain unconfirmed at
  click level — the *business rule* for each is fully defined
  (DB-DESIGN.md §C.4), but the exact portal click sequence is not, so the
  adapter must route to manual completion at exactly that step. The
  ACTIVE/pending outcome for **both** UDISE Import (spec §X) and PEN
  Import (spec "PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED
  WORKFLOW") is now fully confirmed and must be built as ordinary
  automated branches, not `COMING_SOON`.
- **Selector strategy** (spec Final Authority §B, §108/§169/§270): prefer,
  in order — accessible role/name → label/input relationship → stable
  id/name → stable `data-*` → semantic text + DOM context → table
  header/row relationships → student-identity cross-check → URL/route/title
  → controlled fallback discovery → visual evidence (last resort, never
  sole proof of a consequential action). Centralize selectors in portal
  adapters/page objects, never scatter them through workflow code (spec
  §AI.8). Never use fixed coordinates, blind recorded clicks, or `sleep()`
  as the sync mechanism (spec Final Authority §B "Never depend on...").
- **UI-change classification** (spec Final Authority §C): harmless
  presentation change → adapt automatically; semantic-equivalent control
  change → controlled alias/fallback; new known confirmation step →
  versioned adapter rule + verify state; unknown business state → stop
  safely, capture diagnostics, manual intervention. Never invent business
  meaning for an unrecognized state.
- **Consequential-action rule** (spec §D, DB-DESIGN.md §C.3): every write
  to a government portal or spreadsheet follows locate → verify identity →
  verify state → act → verify result → record event → update sheet. Never
  `act → assume success → update sheet`.
- **Student identity verification** (spec §E of Final Authority): use a
  combination of name, father/mother name, surname, DOB, UID/UDISE, PEN,
  class, GR/admission number before any consequential action. A single
  name match is insufficient. Ambiguous → stop for manual review.
- **Retry safety** (spec §G): only retry known-retryable technical failures
  (timeout, transient page load, recoverable navigation). Potentially
  non-idempotent actions (transfer request submission, profile save,
  student initialization) require state verification before any retry —
  enter `VERIFYING`, never blindly repeat.
- **Diagnostics on failure** (spec §H): capture timestamp, student id/name
  snapshot, workflow, current state, URL, title, visible text, screenshot,
  attempted selector strategy, expected vs. observed state, error
  code/message, attempt number, session id, build/version, last verified
  state, retry permission. Never log merely "Element not found".
- **Security boundaries** (spec §I): CAPTCHA and OTP/MFA are always manual.
  Aadhaar `CONSENT FOR DEMOGRAPHIC AUTHENTICATION` / `I Agree` is a
  controlled human-intervention point unless the school explicitly
  authorizes automating that exact action in a compliant manner (open
  question — see DISCOVERY.md). On hitting any of these, pause, tell the
  operator what's needed, resume from checkpoint.
- **Spreadsheet integrity** (spec §J): never mark a row GREEN merely
  because a form was filled, a Save button was clicked, a page navigated,
  or an HTTP call returned without an observed business-success state.
- **Technical failure ≠ business state** (spec §T): timeouts, lost
  confirmations, session expiry, browser crashes, portal outages,
  post-success spreadsheet-write failures, and DB failures all have
  specific required handling — see DB-DESIGN.md / this table — none of
  them may silently become a GREEN, ND, or other business-state write.
- **Secrets** (spec §141/§178, RULEBOOK.md §J6): government portal
  credentials and the Google service-account key are read from the
  git-ignored `credentials/`/`.env` location established in BOOTSTRAP.md.
  Never hardcoded, never logged, never committed.
- **Data normalization** (spec §105/§166/§268): dates, class names, and
  other free-text sheet values are normalized into a canonical internal
  student object *before* being passed to any Playwright action — never
  pass raw spreadsheet cells directly into portal automation (spec §5355).

## Module → spec mapping

### `src/sheets/` — Google Sheets adapter

- Read/write OGR, UDISE, PEN workbooks via the official Google Sheets API
  only — never scrape Sheets through the browser (spec §AD).
- Field mapping layer: spec §104/§167/§269 (per-column mapping,
  documented, not inferred ad hoc at call sites).
- Row-state/color writes must follow DB-DESIGN.md §A.4 vocabulary exactly
  (`GREEN`, `LIGHT ORANGE` + the correct remark) — never rename `REQUEST
  SENT` to `IMPORT PENDING` or vice versa (spec §K).
- IMPORT PENDING tab updates: spec §297 (exact columns per the tab
  structure in DB-DESIGN.md §A.3 — do not invent extra fields).

### `src/engine/` — workflow/state engine

- Implements the state machines in DB-DESIGN.md §C.1-§C.5.
- Condition routing table (data-driven, not scattered if/else — spec §Z):
  class → ID track; UDISE state × PEN state → Condition 1-4 (spec §79/§AA).
- Post-UDISE handoff checkpoint enforcement: spec §33 in full — this is a
  formal gate, not a comment; the automation must be able to answer every
  question in spec §33.12 from stored state before continuing to PEN.
- Green-row skip rule: never reprocess an already-GREEN, verified-complete
  row in ordinary batch processing; an explicit operator-authorized
  recheck action may exist in the UI (spec §AG).

### `src/portals/udise_gujarat/` — Gujarat UDISE page objects

- New entry (CRS-RGI + manual birth routes, CTS fields, five profile tabs,
  Save Student): spec §13-§32, §163, §W. See UI-SPEC.md for the field
  checklist.
- UDISE Import / transfer-request (search by UID, transfer confirmation,
  `Update Transfer Request`, `REQUEST SENT` result): spec §X,
  §294/§298/§9384-9424 (Outcome A/B).
- Completion rule: entire row GREEN only after required profile sections
  verified complete (spec §80/§206).

### `src/portals/udise_plus/` — National UDISE+ / PEN page objects

- New entry (initialization, Aadhaar consent, General/Enrolment/Facility
  Profile, Profile Preview, final "Data completion is complete."): spec
  §34-§53, §164, §Y. See UI-SPEC.md for the field checklist.
- PEN Import/Other-State: spec §299 (Outcome A/B general rule), plus the
  full confirmed click-by-click workflow for the ACTIVE/pending outcome —
  "PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW" (master
  spec, appended 2026-09-25) — Aadhaar-availability check →
  duplicate-Aadhaar routing signal → Track By Details → Global Student
  Search by PEN → Student Status verification → HOS Details capture →
  `IMPORT PENDING` sheet write. See DB-DESIGN.md §C.3a for the state
  machine and new event/error codes. The successful/Dropbox outcome is
  still `COMING_SOON` — do not infer its mechanics from this workflow
  (the spec explicitly warns against this).
- PEN Request Sent (Student Release Request generation): confirmed
  click-level workflow — "PEN REQUEST SENT — STUDENT RELEASE REQUEST
  WORKFLOW" (master spec) — Student Release Request Management → Generate
  Within State → PEN+DOB → Get Details → Admission Detail/remark →
  Generate + confirmation dialog → capture Request No. (e.g.
  `SR/GJ/GJ/305364710` format) → `REQUEST_SENT`/LIGHT ORANGE. Distinct
  portal adapter from the Gujarat transfer-request one (spec §X), sharing
  only the business abstraction (DB-DESIGN.md §C.3d). The National
  "Student Release Request Management" menu has 4 functions (spec
  section 1 above); only **Generate** and **View...(Sent)** are in scope
  — Satyam is always the *destination* school in every documented
  workflow, never the source releasing a student elsewhere, so **Approve**
  and **View...(Inbox)** have no evidenced use case here and are not
  built. Revisit only if a future recording shows Satyam on the source
  side of a release.
- View Sent Request / National approval monitoring: confirmed
  click-level workflow — "HOW TO VIEW SENT REQUEST" (master spec) —
  Student Release Request Management → View...(Sent) → match by Request
  No./PEN/student → read exact status (`"Pending at Destination"` is the
  one confirmed exact wording; preserve `raw_portal_status` always) →
  normalize → feed the same batched §M flow as the Gujarat side. See
  DB-DESIGN.md §C.3b/§C.3c for the state machines.
- ND reconciliation adapter: spec §V/§165/§213/§259-263 (class-first
  search, name match, read PEN, conditional sheet update).
- Completion rule: `PEN = ND` + GREEN is valid success (spec §54/§81/§128.3
  /§180).

### `src/db/` — SQLite schema, DAO layer

- Implements DB-DESIGN.md §B in full, including the append-only
  `pen_case_events` table, controlled statuses/transitions/event codes.
- Reject and log any transition not in DB-DESIGN.md §B.2 as
  `PEN_INVALID_TRANSITION_ATTEMPT` (spec §R/§S).

### `src/diagnostics/` — structured logging + screenshots

- Centralized logging module, not scattered print/log calls (general
  engineering convention — RULEBOOK.md §K4 applies; spec §114/§175/§277
  establish the *content* requirements, listed in "Diagnostics on failure"
  above).

### `src/app/` — PySide6 UI

- See UI-SPEC.md for the screen/checklist inventory. Must surface: batch
  selection, per-student progress, manual-intervention prompts (with the
  reason and what the operator must do), the batched approval-check flow
  (spec §M), Status-Changed manual-review queue with `View Details` /
  `Take Next Action` / `Mark Action Completed` (spec §N), and Approval
  History with multi-filter search + XLSX/CSV export (spec §O).

### `tests/`

- Unit tests: mapping, state transitions, validation, idempotency (spec
  §AI.12).
- Integration/browser tests against mocked/stubbed portal pages where live
  government automation cannot safely be tested (spec §AI.13).
- Testing matrix: see TODO.md (sourced from spec §286).
- UI-change resilience acceptance tests (changed button location/CSS
  class/label, added wrapper div, reordered fields, extra modal, etc.):
  spec §10464-10483 — known-equivalent changes must be absorbed and
  verified; unknown business changes must stop safely with diagnostics.

## Export formats

- Approval History export: XLSX and CSV, must respect the currently active
  filters exactly (spec §O).
- No other export formats are specified.

## Acceptance tests (per feature, before it is reported done)

Use RULEBOOK.md §J11/§J12C verification levels, calibrated by risk:
- Field mapping / normalization / state-transition logic → unit tests
  (Level 2).
- Sheets read/write round-trip → integration tests against a test
  spreadsheet (Level 3), never the school's live production sheets without
  explicit approval (RULEBOOK.md §J8).
- Portal adapters → integration tests against mocked/stubbed pages (Level
  3-4); live-portal verification is an explicitly separate, operator-
  supervised step, never claimed as automated CI evidence (spec §289).
- GREEN/ND/color-write correctness → the acceptance criteria list at spec
  §287, reproduced in TODO.md.

Do not report a workflow "done" without the specific check that verifies
it (RULEBOOK.md §J13) — "the form filled without error" is never
sufficient evidence per spec §J of the Final Authority section.
