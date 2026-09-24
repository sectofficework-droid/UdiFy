# UI-SPEC.md — UdiFy

> Per RULEBOOK.md §E.4. Two UI surfaces exist in this project and must not
> be confused: (1) the **government portals** the app drives — their field
> layout is observed/recorded evidence, not something this project designs
> — and (2) **this application's own PySide6 desktop UI**, which is a
> genuine design deliverable and goes through the normal UI DESIGN gate
> (RULEBOOK.md §F). Section A below indexes (1) for implementation
> reference; Section B is the actual checkbox-driven UI-SPEC for (2).

## A. Government portal field inventory (reference only — not this app's UI to design; verify against live DOM before coding, per spec §W)

### A.1 Gujarat UDISE — new entry (spec §13-§32, §163)

- Student New Entry: CRS-RGI route (BRN, Birth Year/Month/Date, Gender,
  `GET DETAILS FROM CRS-RGI`) or Manual route (Birth State/District/
  Taluka/City/Village, Year/Month/Date, BRN yes/no, Birth Cert PDF upload,
  `Next`).
- CTS new-student fields: child name, father, mother, surname, DOB,
  disabled yes/no (+ type), `ADD NEW STUDENT`.
- Manage Students profile — five tabs, each independently saved:
  1. **Personal** — name/father/mother/surname/guardian, category,
     religion, address (locality/city/district/landmark/road/PIN), mother
     tongue, DOB, gender, Aadhaar-related fields, class; `SAVE STUDENT` /
     `CLEAR`.
  2. **Education** — admission number, admission date, class code, medium,
     previous-class status/result/percentage/attendance, languages/
     subjects (mandatory/additional/co-curricular); class-dependent
     dropdown (PP-3…XII).
  3. **Bank** — do not fabricate values; `NA`/blank is valid when the real
     record has no bank data (spec §29).
  4. **Scholarship & Facility** — exists, part of completion; exact field
     map is a live-DOM verification task (spec §30).
  5. **Health & CWSN** — CWSN status, disability/impairment fields
     (dysgraphia, dyscalculia, dyslexia, ASD, ADHD, etc.), `NA` valid for
     non-CWSN students; exact numbering is a live-DOM verification task
     (spec §31).
- Completion signal: `SAVE STUDENT` + verified success → entire row GREEN.

### A.2 Gujarat UDISE — Import / transfer request (spec §X)

Manage Students → Standard Wise Entry → select class → search by
UID/UDISE → student found at another school → transfer-request
confirmation → Transfer Student page (Transfer From / Transfer To context)
→ `Update Transfer Request` → success message `Student Transfer request
saved successfully.` (submission only, not completion) → Student Transfer
Request List (Sent/Received/Completed/pending filters) → spreadsheet
`REMARK = REQUEST SENT`, LIGHT ORANGE.

### A.3 National UDISE+ — new PEN entry (spec §34-§53, §164)

- Initialize/save new student → success modal `The Student has been
  initialised/Saved Successfully.` (Student Name/Class/Section shown;
  `Add New Student` / `Go to New Entry List` / `Fill General Profile`).
- Four profile stages: **General Profile** (guardian, Aadhaar number +
  name-as-per-Aadhaar with consent dialog `CONSENT FOR DEMOGRAPHIC
  AUTHENTICATION` / `I Agree`, address, pincode, mobile(s), mother tongue,
  social category, religion, BPL/AAY/EWS, CWSN) → **Enrolment Profile**
  (admission number/date, class/section/roll, medium, languages, subjects,
  previous-academic status, RTE 12C, previous result %, attendance days) →
  **Facility Profile** (competitions/olympiads, NCC/NSS/Scouts & Guides,
  height/weight, distance to school [required], parent education level;
  `Back`/`Save`/`Next`) → **Profile Preview** (final modal `Data completion
  is complete.`, `Okay` / `Back to Student Dashboard`).
- Header state while editing shows `Permanent Education Number - Not
  Defined`, `Student AADHAAR Verified`, `CWSN`, `Impairment Type`.
- Completion signal: final modal → PEN cell = `ND` (or real PEN if
  assigned) → entire row GREEN.

### A.4 National UDISE+ — ND reconciliation search (spec §55-64, §165, §V)

Select class first → search by student name → match student → read
current PEN → if real 11-digit PEN, update PEN sheet + OGR; if still
NA, leave `ND` unchanged. Observed list columns: class, PEN, name, gender,
DOB, entry status, last updated, GP/EP/FP indicators, profile/document
icon. Observed statuses: `Not Started`, `In-Progress`, `Completed`.

### A.5 National UDISE+ — PEN Import / Other-State (spec §299, §294-302)

Two outcomes only: Import Successful (student in other school's Dropbox →
UID/PEN obtained → remark `IMPORT SUCCESSFULL` → GREEN) or Import
Pending (student still ACTIVE elsewhere → LIGHT ORANGE, remark `IMPORT
PENDING`, Import sheet updated). Exact button-level sequence beyond this
is a live-portal verification task, not yet fully machine-readable from
the source recording.

## B. This application's own UI (PySide6) — design deliverable, goes through UI DESIGN gate

> Status: **NOT YET DESIGNED.** The source material documents the
> *portals* this app must drive; it does not specify this app's own visual
> design (palette, layout, typography, component inventory, responsive
> behavior are silent). Per RULEBOOK.md §F, UI DESIGN is a separate,
> user-confirmed gate ("UI is final" / "start backend") — do not treat the
> checklist below as final just because it's checkbox-shaped; it is the
> **required inventory of screens/components to design**, not their
   approved look.

### B.1 Required screens (derived from the functional requirements the spec mandates — content, not styling)

- [ ] **Dashboard / batch selection** — pick students ready for processing,
      see their current condition (1-4) and status at a glance.
- [ ] **Run / progress view** — per-student progress through the state
      machine (DB-DESIGN.md §C.1), live status, pause/manual-intervention
      indicator.
- [ ] **Manual intervention prompt** — surfaces exactly what the operator
      must do (CAPTCHA, OTP, Aadhaar consent, unknown-state review) and
      resumes automatically once resolved (spec §I).
- [ ] **Approval / status-check batch flow** — single up-front confirmation
      for all LIGHT ORANGE / REQUEST SENT students (spec §M), then a
      combined report split into **Still Pending** and **Status Changed**.
- [ ] **Status-Changed manual review queue** — `View Details` (full status
      history), `Take Next Action` (opens the student's portal status page),
      `Mark Action Completed` (requires an action description first), case
      remains open until explicitly resolved with a resolution note; reopen
      preserves history and starts a new case cycle (spec §N).
- [ ] **Approval History** — simultaneous filters (Student Name, UID, PEN,
      Request ID, Date, Portal Status, Performed By), search box, Clear/
      Reset, export to XLSX and CSV respecting active filters (spec §O).
- [ ] **ND reconciliation view** — explicit, separately triggered operation
      (never automatic) listing PEN=ND candidates and reconciliation
      results (spec §V).
- [ ] **Diagnostics / logs view** — where captured screenshots and
      structured error context are reviewable without leaving the app
      (spec §H, §114).
- [ ] **Settings / credentials** — where the operator configures Google
      Sheets connection and portal login handling; must never display or
      log secret values in plain text (RULEBOOK.md §J6/§L8).
- [ ] **Automation Coverage** — an explicit, always-visible map of which
      workflow branches are fully automated vs. still manual, and *why*
      (see "COMING_SOON re-analysis" below) — this is the UI's answer to
      spec §AH: never silently guess or silently skip an unresolved
      workflow, show the boundary instead.

### B.2 Palette / typography / component inventory (v1 proposal, 2026-09-25)

**Prototype**: an interactive HTML mock of the four core screens (Batch
Queue, Run & Progress, Approval Monitoring, Approval History) plus the
Aadhaar-consent manual-intervention modal is published at
https://claude.ai/artifact/3XkrooXBVHmWKxAC9pqu9Q and saved locally at
`Scratch/UdiFy/coding/ui-prototype.html` (RULEBOOK.md §F UI-prototype
location — final PySide6 implementation happens at CODING, this is a
visual/interaction reference, not shipped code). This is v1 for review —
iterate per RULEBOOK.md §F ("UI is iterative by default").

**Design rationale**: this is an internal back-office tool for handling
government student records — the visual language leans toward "official
register" (serif display face, ledger-like neutral background) crossed
with "operational software" (a technical sans for UI chrome, a monospace
for the 18-digit UID / 11-digit PEN / dates that are central to this
domain). Status is always shown as color **+** text label together,
mirroring the spec's own rule that the color of a spreadsheet row is never
authoritative on its own (spec §K/§301) — the workflow status text is.

- **Color** (cool, institutional — not the warm-cream/serif/terracotta
  look): `ink` #1C2321 (text), `paper` #EEF2EF (page ground, cool
  ledger-grey, not cream), `surface` #FFFFFF (panels), `indigo` #2E4057
  (primary accent — actions, active nav, focus), `green` #256A42 (semantic
  — GREEN/verified-complete only), `amber` #8A5F16 (semantic — LIGHT
  ORANGE/pending only), `red` #A23E3E (semantic — manual review/error
  only). Full dark-mode token set included in the prototype (the app must
  work correctly in a dark Windows theme too).
- **Type**: `Source Serif 4` for the app name and screen titles (register/
  document gravitas, used sparingly); `IBM Plex Sans` for all UI chrome,
  labels, body text and buttons; `IBM Plex Mono` with tabular figures for
  every UID, PEN, date, and event code — these numeric identifiers are
  literally what this domain runs on and deserve to line up in columns.
- **Layout**: fixed left sidebar (navigation + school/year context) + a
  single main content area per screen; data-dense tables with inline
  status chips rather than separate detail pages, since this is scanned
  and operated by one operator, not browsed.
- **Component inventory established by the prototype**: sidebar nav, stat
  tiles, filter bar (multi-field + search + reset + export), data table
  with status chips and condition badges, a state-machine stepper (Run &
  Progress), a live diagnostic log panel, a manual-intervention alert
  banner + confirmation modal, a status-changed review table with per-row
  actions, expandable diagnostic entries (native `<details>`, no extra
  JS), locked/non-toggleable status rows for rules that are never
  optional (e.g. "Browser visibility: Always on"), and a glossary drawer.
- **Colorfulness (2026-09-25 iteration)**: the user asked for a genuinely
  colorful UI in both themes, and the first pass concentrated color in
  the sidebar/chips only while panels/tables stayed plain white — fixed
  by tinting every panel/table header, adding a soft background glow, and
  a 4-color gradient underline (indigo→teal→marigold→plum, echoing the
  condition-color system) under every page title. The user then rejected
  violet specifically as the sidebar color (tried teal next, then asked
  for dark blue or black — settled on deep navy-blue), and then said the
  overall result "doesn't look good, design it professionally." Correct
  read: coloring nearly everything decoratively (rainbow title
  underlines, multi-hue radial background glow, saturated panel-head
  gradients, tinted stat-tile fills, gradient logo text) read as busy,
  not "colorful and professional" together. Rebuilt around one
  consistent brand color instead: the sidebar's navy blue is now also
  `--indigo` everywhere else (buttons, focus rings, links, Condition 1) —
  previously indigo/violet and the sidebar navy were two unrelated hues.
  Removed the rainbow underline, the multi-hue background glow, and the
  gradient logo text (now solid white). Panels and table headers are
  clean white/neutral again — no forced color tint on every surface.
  Stat tiles switched from filled-background cards to white cards with a
  thin colored left accent bar (a common, restrained "SaaS dashboard"
  pattern). Semantic status colors (green/amber/red) and the categorical
  condition colors (teal/marigold/plum, alongside the shared brand navy
  for Condition 1) are preserved exactly where they carry meaning — chips
  and small badges — which is the actual source of "colorful" now,
  rather than decoration layered on top of every element.
- **Two-color brand system (2026-09-25, final iteration of this pass)**:
  user specified **navy blue + orange** as the two main brand colors,
  with the rest of the palette free for general colorfulness. Navy
  (sidebar, Condition 1 badge, informational callouts, the "Always
  manual" policy category) and orange (primary buttons, focus rings,
  links, the active nav-item accent, the current-step highlight in Run &
  Progress) now divide cleanly: navy reads as "structural/official,"
  orange as "action/attention" — which also gave the existing amber/
  marigold status color (already orange-adjacent, and literally matching
  the real government spreadsheet's LIGHT ORANGE convention for pending
  states) a coherent reason to sit in the same warm family without being
  identical to the brand orange (kept visibly more muted/golden so
  "Always manual" vs "Needs live verification" vs a primary button don't
  collide). Teal/green/red/plum are unchanged, still functional-only
  (Condition 2/success/error/Condition 4 respectively). Deepened both
  brand colors on request ("dark orange for better contrast and dark
  blue") — light-mode orange moved from a mid-tone `#c85a12` to a true
  burnt orange `#a8460a`, navy from `#12335f` to `#0d2547`, sidebar
  gradient deepened to match; dark-mode variants deepened too (less
  pastel/peachy, more saturated) while keeping enough lightness contrast
  against the dark surface to stay legible.
- **Theme toggle added**: the prototype previously only followed the OS/
  browser `prefers-color-scheme` — there was no in-app control, which the
  user asked about. Added a Light/System/Dark segmented toggle in the
  sidebar footer (always visible) and a mirrored control on the Settings
  screen's new "Appearance" panel; both stay in sync, persist the choice
  (`localStorage`, per-device convenience only — a real setting for the
  PySide6 app), and "System" continues to follow the OS. Verified working
  by clicking through to Dark and screenshotting the result — this also
  finally gave a real dark-mode screenshot, which earlier color passes
  couldn't get due to the hosted preview's cross-origin sandbox.
- **Understandability (2026-09-25 iteration)**: added a persistent
  "What do these terms mean?" glossary drawer (UID/UDISE, PEN, ND, GREEN,
  REQUEST SENT, IMPORT PENDING, PH1-3, GR No., Condition 1-4 — plain
  language, grounded in the spec's own vocabulary, not generic
  paraphrases) so an operator unfamiliar with UDISE/PEN terminology isn't
  blocked by jargon. The Diagnostics screen pairs every incident with a
  human-readable "what happened" sentence *and* a short diagnostic ID
  (RULEBOOK.md §L8 pattern) rather than a raw error/stack trace.

### B.3 Responsive behavior

N/A in the usual sense — this is a native Windows desktop app (PySide6),
not a browser page. The HTML prototype still collapses to a single column
below ~760px purely so it stays reviewable on any device; actual
minimum-window-size behavior for the PySide6 app is a CODING-time decision
informed by, but not identical to, the web mock's breakpoint.

### B.4 Interactions checklist (content requirements only, no styling yet)

- [ ] Manual-intervention prompts must block only the affected student, not
      the whole batch, unless continuing risks incorrect data (spec §T).
- [ ] Diagnostic IDs surfaced to the operator, not raw stack traces
      (RULEBOOK.md §L8) — applies to this app's own errors, distinct from
      government-portal diagnostics captured in B.1's Diagnostics view.
- [ ] No consequential action (GREEN write, transfer-request submission,
      Aadhaar consent automation) is ever available as a single accidental
      click without the verification sequence in IMPL-SPEC.md having run.

### B.5 COMING_SOON re-analysis (2026-09-25 — re-read of spec §184/§215/§221/§281/§294-302/§W-§Y against the "FINAL AUTHORITY" section's precedence rule)

The user asked for a fresh pass on the spec's `COMING_SOON`/`MANUAL_REQUIRED`
boundary (§AH) specifically, to make sure the UI never implies more
automation coverage than the evidence actually supports. Earlier sections
(§184, §215, §221, §281) list broad "import workflow unknowns" — but those
predate the later Import recordings being incorporated, and the spec's own
"FINAL AUTHORITY" section (§9542+) explicitly supersedes contradictory
earlier statements. Re-checking what's *actually still* unresolved after
that later section:

| Workflow | Status | Why |
|---|---|---|
| UDISE New Entry (all 5 profile tabs) | Automated | Full click sequence confirmed, spec §163/§W |
| &nbsp;&nbsp;↳ Scholarship & Facility / Health & CWSN exact fields | Needs live-DOM verification | Spec §30/§31/§W: "not completely machine-readable in every frame" |
| PEN New Entry (4 profile stages) | Automated | Full click sequence confirmed, spec §164/§Y |
| &nbsp;&nbsp;↳ Aadhaar consent | Always manual (policy) | Spec §39/§142/§I — legal confirmation, not an evidence gap |
| UDISE Import — pending/request-sent outcome | Automated | Exact click sequence confirmed, spec §X |
| UDISE Import — successful/Dropbox outcome | **Manual for now** | Outcome *rule* confirmed (spec §295) but spec §295.3 itself says exact portal screen/button names "must be documented from the dedicated Import recordings rather than invented" — not yet given at click level |
| PEN Import — Other School ACTIVE (pending) outcome | **Automated** *(updated 2026-09-25)* | User re-checked the recording directly and supplied the full click-by-click workflow — "PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW", appended to the master spec. Includes the Aadhaar-duplicate-check routing signal, Track By Details, Global Student Search by PEN, Student Status verification, HOS Details capture, and the `IMPORT PENDING` sheet write. |
| PEN Import — successful/Dropbox outcome | **Manual for now** | Still not demonstrated by any recording — the new section explicitly says so (its own §19/§27) and warns not to infer it from the ACTIVE-outcome workflow |
| Condition 4 — both imports resolve to their *pending* outcome | **Automated** *(updated 2026-09-25)* | Composable from two now-confirmed pieces: UDISE Import ACTIVE (spec §X) + PEN Import ACTIVE (new section above) run independently for the same student |
| Condition 4 — either import resolves to its *successful/Dropbox* outcome | **Manual for now** | Composition includes an unconfirmed piece; spec §221/§281 flag "Exact Condition 4 combined sequence" and no recording demonstrates the successful path for either portal |
| ND reconciliation | Automated | Full sequence confirmed, spec §V/§165 |
| Gujarat transfer-request status monitoring | Automated | Full rule confirmed, spec §M-§O, §X |
| PEN Request Sent (Student Release Request generation) | **Automated** *(added 2026-09-25)* | User re-checked `PEN REQUEST SENT.mp4` directly; full click sequence now in the master spec's "PEN REQUEST SENT — STUDENT RELEASE REQUEST WORKFLOW" section |
| View Sent Request / National release-request monitoring | **Automated** *(added 2026-09-25)* | User re-checked `HOW TO VIEW SENT REQUEST.mp4` directly; confirmed exact status wording ("Pending at Destination") and request-list fields, master spec "HOW TO VIEW SENT REQUEST" section |
| CAPTCHA / OTP | Always manual (policy) | Spec §I — security boundary, not an evidence gap |

**Important distinction preserved from the spec:** `IMPORT PENDING`
(student still ACTIVE elsewhere, no request generated) and `REQUEST SENT`
(a release/transfer request was actually generated and returned a request
number) are both automated now, but they are **not the same business
state** even though both render LIGHT ORANGE — see DB-DESIGN.md §C.3d.
Do not merge them in the UI or the database.

This table is now the authoritative "what's really unresolved" list —
IMPL-SPEC.md's module mapping and TODO.md's build order should treat the
**Manual for now** rows as `COMING_SOON` adapter boundaries (spec §AH:
implement the boundary, mark it, never guess), not as ordinary build tasks
that will "just work" once coded. Distinguish this from **Always manual
(policy)**, which is a permanent design decision, not a gap to eventually
close. As of 2026-09-25 (updated twice this day as the user re-checked two
more recordings), only the **successful/Dropbox outcome** (for either
UDISE or PEN Import, and any Condition-4 combination that includes one)
remains genuinely unconfirmed. Everything else in this project's nine
source recordings — including PEN Import's ACTIVE/pending outcome, PEN
Request Sent, and View Sent Request — is now fully confirmed at click
level. No workflow should be reported to the user as "still needs the
video" or "undocumented" beyond that one remaining boundary.

**UI treatment**: added a dedicated **Automation Coverage** screen (the
table above, in operator-facing language) to the prototype, plus a dashed
plum "Manual for now" chip used inline wherever the queue/run view would
otherwise imply full automation (e.g. a Condition 4 student's PEN status).
This directly answers "make sure no functionality is missing" — rather
than the UI silently doing nothing for an unresolved workflow, it now
explicitly shows *that* it's unresolved and *why*, everywhere it's
relevant, not just in one buried settings page. See
https://claude.ai/artifact/3XkrooXBVHmWKxAC9pqu9Q (v4).

### B.6 Full spec-vs-implementation audit (2026-09-25, before UI confirmation)

User asked for a complete recheck — every line of the master spec against
the UI — before moving to UI confirmation. Ran a systematic pass covering
the ~7,000 lines of the spec not yet fully read this session (confirmed:
pure restatement across multiple full-document rewrites, nothing new)
plus a full cross-check of every UI-relevant requirement against the live
prototype and this file. Result: two real, spec-cited gaps, one data bug
in the mock, two polish items — all fixed:

- **Manual Intervention Controls** (spec §116/§176/§279, the same
  10-item list repeated verbatim three times) — 4 of 10 were missing:
  **Pause**, **Retry**, **Open Student**, **Mark for Manual Review**.
  Added a Student Detail drawer (click any Batch Queue student name) that
  now houses all four as explicit operator controls, plus a batch-level
  "Pause batch" control on Run & Progress and a "Retry this student"
  button on a recoverable Diagnostics entry.
- **Approval History filters** (spec §O / this file's own §B.1) required
  7 fields; only 5 existed. Added the missing **Request ID** and
  **Portal Status** filters.
- **Data bug**: the Run & Progress manual-intervention example used Riya
  Chauhan (Condition 3, UDISE not yet GREEN per Batch Queue) mid-PEN-
  branch — impossible under the UDISE-before-PEN gate (spec §130/§207).
  Swapped the example to Ishita Solanki, whose Batch Queue state (UDISE
  GREEN, PEN in progress) actually supports being mid-PEN-branch.
- Minor: de-duplicated a reused Request No. example value; added a
  "LIGHT ORANGE" glossary entry; documented in IMPL-SPEC.md why the
  National portal's Approve/View-Inbox functions are out of scope
  (Satyam is always the destination school in every recording, never the
  source).
- Confirmed with no violations found: nothing in the UI implies more
  automation/certainty than the spec supports — every `COMING_SOON`
  boundary still shows correctly as "Manual for now," nowhere else.

All fixes verified live via the browser tool (student drawer opened with
correct data, both action buttons changed state, batch pause toggled,
diagnostics retry button present, all 7 History filters render, the
Ishita Solanki swap is consistent across Run & Progress/Diagnostics/the
manual-intervention modal). Republished (v16):
https://claude.ai/artifact/3XkrooXBVHmWKxAC9pqu9Q

### UI DESIGN gate status

**In progress — all 9 screens in B.1 now mocked** (Batch Queue, Run &
Progress, Approval Monitoring, Approval History, ND Reconciliation,
Diagnostics, Automation Coverage, Settings) plus the manual-intervention
modal and the glossary drawer, as of 2026-09-25. Iterating per RULEBOOK.md
§F until the user says **"UI is final" / "start backend."**
