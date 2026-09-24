# DB-DESIGN.md — UdiFy

> Per RULEBOOK.md §E.2. Two data stores exist and must never be conflated
> (spec §AF): the **three Google Sheets workbooks** (the school's system of
> record — OGR / UDISE / PEN) and the **local SQLite workflow/audit
> database** (this application's own state — never the source of truth for
> student identity, never a replacement for the OGR).

## A. Spreadsheet data model (external system of record — read/write via Sheets API, not owned by this app)

### A.1 ONLINE GENERAL REGISTER (OGR) — spec §4, §156.1, §229

Every student is recorded here, in stages. Columns observed:
`AY, NAME, STD, MOBILE 1, MOBILE 2, PR, T-GR, TC, DOB, DOA, DOE, AADHAR,
UID, PEN, APAAR, DOCUMENTS PENDING`.

**Invariant (hard rule, spec §4.4/§128.4):** OGR row color never becomes
GREEN as part of government-entry completion. OGR UID/PEN cells are
updated as the underlying government process completes, but row color is
untouched by that process.

### A.2 UDISE_Entry_(State) — spec §5, §157, §230

Tabs: `PH1`, `PH2`, `PH3` (operational batches, not separate schemas — spec
§AB/§133). Headers (29 columns): `REMARK, Class, UDISE No, Birth Cert Reg
No, Birth Year, Birth Month, Birth Date, Gender, Birth State, Birth
District, Birth City, Student Name, Father's Name, Mother's Name, Surname,
Date of Birth, GR No, Roll No, Plot Number, Society, Landmark, Area, Pin
Code, Mother Tongue, Date of Join, Aadhar Card No, Name as per Aadhar,
Mobile No 1, Mobile No 2`. PH3 may contain one extra unused column — do not
treat it as a business field without live evidence.

**Invariant (spec §6, §80, §128.1, §206):** completion = **entire row**
GREEN, only after the required profile sections are verified complete, not
merely on UID generation.

### A.3 PEN_Entry_(National) — spec §7, §158, §231

Tabs: `PH1`, `PH2`, `PH3`, `IMPORT PENDING`. Main headers (22 columns):
`PEN, Class, Student Father Surname, Gender, Date of Birth, Student State
Code (UDISE No), Mother's Name, Father's Name, Aadhar Number of Student,
Name of Student as per Aadhar Card, Admission Date, Full Address, Pincode,
Mobile No 1, Mobile No 2, Mother Tongue, Admission Number in Present
School (GR No), Roll No, Previous Class Percentage, Previous Class
Attendance Days, Height (cm), Weight (kg)`.

`IMPORT PENDING` tab headers (13 columns): `SR NO, STUDENT NAME, PEN, DOB,
SCHOOL NAME, SCHOOL UDISE, STATE, DISTRICT, BLOCK, HEADMASTER, CONTACT NO,
STATUS, REMARK`.

**Invariant (spec §54, §81, §128.2-3):** `PEN = ND` + row GREEN is a valid
**completed** New-PEN state — `ND` means the portal legitimately has no
PEN yet (`Portal NA → Spreadsheet ND`, spec §U), it is never treated as
failure.

### A.4 Row-state / color vocabulary (must not be renamed or conflated — spec §K, §72, §301)

| Value | Meaning | Applies to |
|---|---|---|
| GREEN | Verified completion of the applicable workflow | UDISE row, PEN row (never OGR row for gov-entry completion) |
| LIGHT ORANGE + remark `REQUEST SENT` | Transfer request submitted, awaiting destination action | UDISE Import / transfer-request flow |
| LIGHT ORANGE + remark `IMPORT PENDING` | Import attempted, student still ACTIVE in other school | UDISE/PEN Import flow |
| `ND` (PEN cell) | Not Defined — portal returned no PEN yet; can coexist with GREEN | PEN sheet |
| Unchanged / default | Not yet processed, or mid-workflow | any |

`REQUEST SENT` and `IMPORT PENDING` are both LIGHT ORANGE visually but are
**different workflow states** — the database/workflow status field is
authoritative, never the color alone (spec §2 of Final Reconciliation
section, §302).

## B. Local application database (SQLite — this app's own state, spec §AF)

Stores: normalized student identity/reference, spreadsheet source
metadata, workflow condition, portal state, job/run state, checkpoints,
retries, errors, screenshot/diagnostic references, approval history, PEN
case state, immutable PEN events, manual interventions, authorization
records, resolution/reopen history. It is explicitly **not** the OGR and
never becomes the source of truth for student identity.

### B.1 `pen_case_events` — append-only, immutable (spec §P)

| Column | Type | Notes |
|---|---|---|
| `event_id` | TEXT PK | UUID |
| `case_id` | TEXT NOT NULL | |
| `case_cycle_id` | TEXT NOT NULL | UUID; a reopen starts a **new** cycle id, history stays immutable (spec §S) |
| `student_id` | TEXT NOT NULL | |
| `student_name` | TEXT NOT NULL | snapshot at event time |
| `pen` | TEXT NULL | valid 11-digit PEN or `ND` |
| `uid_udise` | TEXT NULL | |
| `workflow` | TEXT NOT NULL | |
| `event_code` | TEXT NOT NULL | see B.3 |
| `event_version` | INTEGER NOT NULL | positive |
| `previous_event_id` | TEXT NULL | required except first event in a cycle |
| `case_status_before` | TEXT NOT NULL | see B.2 |
| `case_status_after` | TEXT NOT NULL | see B.2 |
| `portal_status` | TEXT NULL | exact portal wording, preserved verbatim |
| `portal_status_previous` | TEXT NULL | |
| `spreadsheet_status` | TEXT NOT NULL | snapshot |
| `spreadsheet_color` | TEXT NOT NULL | snapshot |
| `action_description` | TEXT NULL | mandatory for manual-action events |
| `resolution_note` | TEXT NULL | mandatory for resolution/closure |
| `reopen_reason` | TEXT NULL | mandatory for reopen |
| `error_code` | TEXT NULL | mandatory for failure events |
| `error_message` | TEXT NULL | mandatory for failure events |
| `attempt_number` | INTEGER NULL | positive, for retry events |
| `authorized_by` | TEXT NULL | mandatory for consequential user authorization |
| `performed_by` | TEXT NOT NULL | `AUTOMATION` or `MANUAL` |
| `environment` | TEXT NOT NULL | `MOCK` or `LIVE` — mandatory, never inferred from context (decision 2026-09-25, master spec "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION" §5). A `MOCK` event must never be capable of triggering a real spreadsheet write or a `LIVE_VERIFIED_SUCCESS` case status. |
| `occurred_at` | TEXT NOT NULL | ISO-8601, timezone-aware |
| `created_at` | TEXT NOT NULL | |
| `metadata_json` | TEXT NULL | valid JSON |
| `event_hash` | TEXT | recommended, tamper-evidence |
| `previous_event_hash` | TEXT | recommended, tamper-evidence |

### B.2 Controlled PEN case statuses (spec §Q)

`ACTION_REQUIRED`, `RETRYING`, `VERIFYING`, `MANUAL_REVIEW`, `RESOLVED`,
`UNRESOLVED_CLOSED`, `REOPENED`. Performers: `AUTOMATION`, `MANUAL`.

Allowed transitions (spec §S) — reject and log anything else as
`PEN_INVALID_TRANSITION_ATTEMPT`:

```text
ACTION_REQUIRED → RETRYING | VERIFYING | MANUAL_REVIEW
RETRYING        → ACTION_REQUIRED (after failure) | VERIFYING
VERIFYING       → <result-derived state>
MANUAL_REVIEW   → <manual action / resolution path>
RESOLVED            → REOPENED   (only)
UNRESOLVED_CLOSED   → REOPENED   (only)
REOPENED        → VERIFYING | ACTION_REQUIRED | MANUAL_REVIEW
```

Resolution requires manual authorization + a resolution note (+ final
verified portal state where applicable). A reopen creates a new
`case_cycle_id`; nothing is overwritten.

### B.3 Controlled PEN event codes (minimum set, spec §R)

`PEN_ACTION_REQUIRED_OPENED, PEN_RETRY_STARTED, PEN_RETRY_FAILED,
PEN_VERIFICATION_STARTED, PEN_VERIFICATION_RESULT, PEN_UNRESOLVED,
PEN_MANUAL_ACTION_STARTED, PEN_MANUAL_ACTION_COMPLETED,
PEN_RESOLUTION_STARTED, PEN_RESOLVED, PEN_SPREADSHEET_UPDATE_AUTHORIZED,
PEN_SPREADSHEET_UPDATE_COMPLETED, PEN_SPREADSHEET_UPDATE_FAILED,
PEN_CASE_REOPENED, PEN_REOPEN_VERIFICATION, PEN_REOPENED_ACTION_REQUIRED,
PEN_UNRESOLVED_CLOSED, PEN_CASE_REOPENED_AFTER_UNRESOLVED,
PEN_INVALID_TRANSITION_ATTEMPT`.

### B.4 Other required SQLite tables (names are implementation choices; the data these hold is mandated by spec §AF — design during CODING setup, not invented here)

- **students** — normalized identity/reference (name, father/mother name,
  surname, DOB, class, GR/admission no., Aadhaar, UID/UDISE, PEN, sheet row
  refs) used for the multi-attribute identity check (spec §E of Final
  Authority) before every consequential action.
- **workflow_runs / jobs** — batch/run state, checkpoints, resumability
  (spec §174, §219); also carries `environment = MOCK | LIVE` per run, for
  the same reason as `pen_case_events.environment` above.
- **portal_sessions** — session/login state per portal (spec §112, §173).
- **retry_log** — attempt number, retryable vs non-idempotent classification
  (spec §G of Final Authority, §88).
- **diagnostics** — screenshot/URL/title/DOM-state references tied to a
  student + event (spec §H of Final Authority, §114).
- **approval_checks** — batched transfer/release-request status-check
  runs across both portals, with `Still Pending` vs `Status Changed`
  classification (spec §M) and per-request `raw_portal_status` /
  `normalized_status` (spec §C.3c above).
- **import_outcomes / request_cases** — Import Successful vs Import
  Pending vs Release/Transfer Request Sent records, carrying `case_type` /
  `portal` / `request_type` (spec §C.3d above) and feeding the `IMPORT
  PENDING` sheet tab update requirement (spec §297).

Exact column lists for these are an implementation-time task (spec §AI.7:
"implement data models and state machines before consequential browser
actions") — they must be designed against the fields this document and the
master spec actually require, not invented ahead of need; update this file
when they are finalized (RULEBOOK.md §J12A change-impact rule applies if
the shape changes materially from what's described here).

## C. State machines

### C.1 Main per-student workflow (spec §78, §201.2, §D of Final Authority)

```text
READ_SHEETS → VALIDATE_STUDENT → DETERMINE_CLASS_ROUTE →
DETERMINE_ENTRY_CONDITION → RUN_UDISE_BRANCH → VERIFY_UDISE →
RUN_PEN_BRANCH → VERIFY_PEN → UPDATE_SHEETS → LOG_SUCCESS
```

Condition routing (spec §79):

```text
Determine UDISE state: NEW or IMPORT
  NEW    → Determine PEN state: NEW → Condition 1 | IMPORT → Condition 2
  IMPORT → Determine PEN state: NEW → Condition 3 | IMPORT → Condition 4
```

### C.2 Post-UDISE handoff checkpoint (spec §33, mandatory before PEN starts)

```text
UDISE_STATUS = VERIFIED_COMPLETE, UID = <real value>,
OGR_UID = populated, OGR_PEN = pending, UDISE_ROW = GREEN,
OGR_ROW = unchanged, PEN_STATUS = NOT_YET_COMPLETE
```
Persisted so the app can resume safely if closed before PEN processing
begins. Failure cases (UID missing / row not GREEN / inconsistent state /
PEN already real / PEN=ND ambiguity) are enumerated at spec §33.9 — each
routes to manual review, never a guess.

### C.3 Consequential-action rule (applies to every write, spec §4/§D)

```text
Locate target → Verify student identity → Verify current portal state →
Perform action → Wait for state transition → Verify expected result →
Record immutable event → Only then update spreadsheet workflow state
```

### C.3a PEN Import — Other School ACTIVE (confirmed 2026-09-25, spec "PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW", appended at the end of the master spec)

```text
OPEN_ADD_NEW_STUDENT → CHECK_AADHAAR_AVAILABILITY → ENTER_AADHAAR →
SUBMIT_AADHAAR_CHECK →
  Aadhaar available            → ordinary New PEN path (§C.1)
  Aadhaar already registered   → EXISTING_STUDENT_FOUND_BY_AADHAAR
  unknown/error                → MANUAL_REQUIRED
        ↓ (existing student)
READ_TRACK_BY_DETAILS → VERIFY_STUDENT_IDENTITY →
OPEN_GLOBAL_STUDENT_SEARCH → SEARCH_BY_PEN → READ_STUDENT_RESULT →
VERIFY_STUDENT_STATUS →
  ACTIVE          → READ_HOS_DETAILS → WRITE_IMPORT_PENDING →
                     IMPORT_PENDING / LIGHT ORANGE
  NOT ACTIVE / unknown → MANUAL_REQUIRED (not invented from this evidence)
```

This is the *pending* outcome specifically — confirmed at click level. The
*successful* (student found in the other school's "Dropbox") PEN Import
outcome is a separate, still-undocumented path (DB-DESIGN.md §C.4/§AF) —
do not infer it from this state machine.

New controlled codes this workflow introduces (append to the event-code
set in §B.3, same table/immutability rules apply):
`EXISTING_STUDENT_FOUND_BY_AADHAAR`, `IMPORT_PENDING_ACTIVE_OTHER_SCHOOL`,
`PEN_AADHAAR_CHECK_FAILED`, `PEN_EXISTING_STUDENT_DETAILS_UNAVAILABLE`,
`PEN_STUDENT_MATCH_AMBIGUOUS`, `PEN_SEARCH_NO_RESULT`.

Required verification before writing the `IMPORT PENDING` sheet record:
student name match + valid 11-digit PEN + portal result belongs to the
intended student; source school name/UDISE/state/district/block captured;
HOS name/contact captured when available; portal explicitly shows
`ACTIVE` (never inferred). Idempotency: on restart, check SQLite state and
the `IMPORT PENDING` sheet by stable identifiers (student id/name, PEN,
UID, source-school UDISE) before repeating the Aadhaar check or creating a
duplicate pending row.

### C.3b PEN Request Sent — Student Release Request generation (confirmed 2026-09-25, spec "PEN REQUEST SENT — STUDENT RELEASE REQUEST WORKFLOW")

```text
OPEN_STUDENT_RELEASE_REQUEST_MANAGEMENT → GENERATE_WITHIN_STATE →
ENTER_PEN_AND_DOB → GET_DETAILS → VERIFY_STUDENT →
FILL_ADMISSION_DETAIL_AND_REMARK → GENERATE_REQUEST →
CONFIRMATION_DIALOG → CONFIRM → WAIT → verify success message
("Release Request successfully generated") → capture Request No.
(e.g. `SR/GJ/GJ/305364710` — format only, never hardcode) →
REQUEST_SENT / LIGHT ORANGE, remark = REQUEST SENT
```

This is a National UDISE+ workflow, distinct from — but sharing the same
business abstraction as — the Gujarat UDISE transfer-request flow
(spec §X). Do not implement them as one shared browser workflow.

### C.3c Viewing/monitoring a sent National PEN request (confirmed 2026-09-25, spec "HOW TO VIEW SENT REQUEST")

```text
Student Release Request Management → View Student Release Request(s)
Within State (Sent) → match Request No./PEN/student → read Request
Status (raw) → normalize → compare to previously recorded status
  unchanged ("Pending at Destination")  → no action, record check event
  changed                                → STATUS_CHANGED, manual review
  unrecognized wording                   → UNKNOWN_PORTAL_STATUS, manual review
```

Feeds the same batched approval-check flow as the Gujarat side (spec §M,
this file's cross-cutting operations) — one operator confirmation checks
every eligible `REQUEST SENT`/LIGHT ORANGE case across **both** portals.

### C.3d Request-case data model — do not collapse IMPORT PENDING and REQUEST SENT (spec "SHARED REQUEST-CASE MODEL AND DATABASE STATE REQUIREMENTS")

Row color (LIGHT ORANGE) is presentation only. The request-case table
(§B.4's `import_outcomes`/`approval_checks`, or a merged `request_cases`
table — finalize the exact table split at CODING time) must carry
structured fields, not just color/remark:

```text
case_type:     IMPORT_PENDING_ACTIVE | RELEASE_REQUEST_SENT | TRANSFER_REQUEST_SENT
portal:        NATIONAL_UDISE | GUJARAT_UDISE
request_type:  NONE | RELEASE_REQUEST | TRANSFER_REQUEST
raw_portal_status:  exact wording as returned by the portal, always preserved
normalized_status:  a known enum value, or UNKNOWN_PORTAL_STATUS if unmapped
```

A student is never represented internally as merely `LIGHT_ORANGE` —
`case_type = IMPORT_PENDING_ACTIVE, request_type = NONE` and `case_type =
RELEASE_REQUEST_SENT, request_type = RELEASE_REQUEST` are different rows
even though both render LIGHT ORANGE in the spreadsheet.

### C.4 Import outcome classifier (spec §300)

```text
IMPORT_ATTEMPT → read portal result
  successfully imported (Dropbox)? YES → GREEN, write UID/PEN,
                                          remark = IMPORT SUCCESSFULL
                                   NO  → student ACTIVE elsewhere? 
                                          YES → LIGHT ORANGE,
                                                remark = IMPORT PENDING,
                                                update Import sheet(s)
                                          NO/UNKNOWN → MANUAL REVIEW
```

### C.5 ND reconciliation (spec §V, separate operation — never automatic)

```text
open National UDISE+ Student DB → select class FIRST → search by name →
match correct student → read current PEN
  real 11-digit PEN found → replace ND in PEN sheet + OGR, keep audit trail
  still NA/no PEN         → leave ND unchanged
```

### C.6 Adapter interfaces (mock-first architecture, decision 2026-09-25)

Every external dependency this schema's state machines interact with is
reached through an interface, never a concrete SDK/class directly — full
detail in the master spec's "CREDENTIALS, MOCKING AND LIVE VERIFICATION
DECISION". Interfaces relevant to this document:

```text
StudentSheetRepository            (reads/writes everything in section A above)
        |-- GoogleSheetsRepository   (real; Google Sheets API)
        |-- MockSheetsRepository     (in-memory; every workflow above must
                                       run to completion against this one)

GujaratUDISEPortalAdapter          (§C.1's UDISE branch, §X's Import branch)
NationalUDISEPortalAdapter         (§C.1's PEN branch, §C.3a/b/c's Import/
                                     Request Sent/View Sent Request branches)
```

The two portal adapters are never merged into one class, even though they
share the request-case abstraction in §C.3d. Every state machine in this
document (§C.1-§C.5) must be exercised against mocked implementations of
these interfaces before any live credential is configured — the state
machine's logic does not change between mock and live, only which
concrete adapter is injected.

## D. Key calculations / derived values

- Class → ID-track routing: JrKG/SrKG/Balvatika/1st → Satyam School ID;
  2nd+ → Block ID (spec §12/§Z).
- UID/UDISE = 18-digit value; PEN = 11-digit value when actually assigned
  (spec §9/§U). Never derive one from the other; never reuse example values
  as constants (spec §102/§186).

## E. Seed data

None specified — no seed/demo dataset exists in the source material. Test
fixtures (mocked/stubbed portal pages, spec §AI.13) are a CODING-phase
deliverable, not seed data for the real spreadsheets.

## F. Acceptance notes

See PLAN.md "Progress rules" and TODO.md's testing matrix (spec §286-287)
for the conditions under which this schema is considered correctly
implemented (state transitions covered, invalid transitions rejected and
logged, append-only event table never mutated).
