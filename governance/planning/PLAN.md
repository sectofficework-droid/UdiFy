# PLAN.md — UdiFy

> Per RULEBOOK.md §E.1. Source of truth for every business rule remains
> `governance/planning/UDIFY-SPECIFICATIONS.md` (cited as "spec §N" below).
> This file is the engineering plan built on top of it; it never
> contradicts the spec — if it appears to, the spec wins (per the spec's
> own "FINAL SOURCE-OF-TRUTH RULE").

## Scope

A Windows desktop automation application for Satyam Stars International
School that:
1. Reads student records from three Google Sheets files (OGR,
   `UDISE_Entry_(State)`, `PEN_Entry_(National)`) — spec §3-§8, §156-158.
2. Classifies each student into one of four entry conditions — spec §11/
   §AA/§149/§159.
3. Routes by class to the correct portal/ID track (Satyam School ID vs
   Block ID) — spec §12/§Z/§160/§233.
4. Drives the Gujarat UDISE and National UDISE+ portals through a real,
   visible Playwright browser to complete UDISE and PEN workflows,
   including Import/transfer-request variants — spec §13-§53, §163-164,
   §294-302, §W/§X/§Y.
5. Verifies every consequential portal action before writing back to the
   spreadsheets — spec Final Authority §D/§J.
6. Maintains its own local SQLite workflow/audit database (checkpoints,
   retries, the immutable `pen_case_events` chain, approval history) — spec
   §AF, §P-§S.
7. Supports ND reconciliation and batched transfer-request approval
   monitoring as separate, explicit operations — spec §V, §M-§O.
8. Never invents unobserved government-portal behavior — unresolved
   workflows are explicit `COMING_SOON` / `MANUAL_REQUIRED` adapters — spec
   §AH.

## Stack (confirmed 2026-09-25, RULEBOOK.md §A9/§C2 clarify round)

| Layer | Choice | Spec ref |
|---|---|---|
| Language | Python | §AE, §76, §275 |
| Desktop UI | PySide6 | §AE |
| Browser automation | Playwright, headed/visible only | §AE, §140, §276 |
| Local state/audit DB | SQLite | §AE, §AF |
| Spreadsheet integration | Google Sheets API (official API, never scraped) | §AD |
| Spreadsheet import/export | openpyxl | §AE |
| Packaging | **None — removed 2026-09-27.** UdiFy runs from source via `.venv\Scripts\pythonw.exe`; see "Deliberate gaps" under File map | §AE, §76 |

Real installed versions to record in BOOTSTRAP.md once the project
virtualenv is created: Python 3.14.7 confirmed on this machine
(`C:\Python314\python.exe`); package versions (PySide6, Playwright, etc.)
to be pinned in `requirements.txt` during CODING setup, not guessed here.

## Modules / features (maps to IMPL-SPEC.md file-by-file detail)

1. **Sheets adapter** — Google Sheets API read/write for OGR, UDISE, PEN
   workbooks; normalizes rows into an internal student object before any
   portal action (spec §104/§167/§269, §5355).
2. **Workflow/state engine** — the `READ_SHEETS → VALIDATE_STUDENT →
   DETERMINE_CLASS_ROUTE → DETERMINE_ENTRY_CONDITION → RUN_UDISE_BRANCH →
   VERIFY_UDISE → RUN_PEN_BRANCH → VERIFY_PEN → UPDATE_SHEETS → LOG_SUCCESS`
   state machine (spec §78), plus the separate `CHECK_ND_PEN` and
   transfer-request-approval-monitoring flows.
3. **Portal adapters (page objects)** — one per portal surface: Gujarat
   UDISE new-entry, UDISE Import/transfer-request, National UDISE+ new-PEN,
   PEN Import/Other-State, ND reconciliation search, approval/status
   monitoring. Never a monolithic script (spec §AI.8).
4. **SQLite state/audit layer** — checkpoints, retries, errors, screenshots
   references, `pen_case_events`, approval history (spec §AF, §P).
5. **PySide6 GUI** — batch selection, progress, manual-intervention
   prompts, approval-history filter/export UI (spec §M-§O).
6. **Diagnostics/logging** — structured local logging + screenshot capture
   on any unexpected state (spec §114/§175/§277, §H of Final Authority).

## Workflow (high level)

See DB-DESIGN.md for the full state machine and DISCOVERY.md REQ-001..010
for the journey list. Architecture diagram (spec §77):

```text
                    PySide6 Desktop UI
                               |
                  Workflow / State Engine
                          |        |
                 Sheets Adapter   Playwright Browser
                       |              |
               Google Sheets   Gujarat UDISE + UDISE+ National
               (OGR/UDISE/PEN)
                          |
                   SQLite State + Logs
```

## File map (production code, at ROOT — created starting at CODING gate)

**As built, 2026-09-27.** This is the real, verified layout — reconciled
with the original sketch above, which predated several decisions:

```
UdiFy/
├── run_udify.py                 entry point (launched via .venv\Scripts\pythonw.exe)
├── requirements.txt             exact pinned versions
├── pytest.ini                   test config
├── .env                         LOCAL, git-ignored — never committed
├── .env.example                 trackable template, no real values
│
├── src/                         all production code, mirrors the architecture
│   ├── app/                     PySide6 GUI
│   │   ├── main.py              entry point called by run_udify.py
│   │   ├── main_window.py       sidebar nav + single content area
│   │   ├── app_context.py       shared state: settings, DB, sheets repo
│   │   ├── portal_factory.py    THE real-vs-mock decision point (LIVE)
│   │   ├── run_worker.py        background QThread running a condition engine
│   │   ├── screens/             one module per UI-SPEC.md §B.1 screen
│   │   ├── theme.py             navy/orange palette + stylesheet
│   │   └── widgets.py           shared small components
│   ├── engine/                  workflow/state engine, condition routing
│   │   ├── entry_router.py      spec §78/§79 decision tree → Conditions 1-4
│   │   ├── branches.py          the shared per-portal workflow branches
│   │   ├── condition1..4.py     one engine per entry condition
│   │   ├── field_mapping.py     sheet row → portal form fields
│   │   ├── audit.py             pen_case_events writes
│   │   └── resilience.py        timeout/crash classification
│   ├── sheets/
│   │   ├── models.py            Student / SheetRowRef value objects
│   │   └── repository.py        StudentSheetRepository + Mock/Google impls
│   ├── portals/
│   │   ├── base.py              shared portal exceptions + generic helpers
│   │   ├── udise_gujarat/       Gujarat UDISE (state) adapter
│   │   └── udise_plus/          National UDISE+ adapter
│   ├── db/                      SQLite schema + one module per table
│   ├── diagnostics/             structured logging, redaction, capture
│   └── config/                  settings loading (.env), settings_writer
│
├── tests/
│   ├── unit/                    pure logic, no browser
│   ├── integration/             real Playwright against the fixture pages
│   ├── fixtures/                the MOCK portal pages + generic helper fixture
│   └── live/                    reserved for committed live-verification
│                                scripts — currently EMPTY (see note below)
│
├── credentials/                 git-ignored — service-account JSON
├── diagnostics/                 git-ignored — runtime logs/screenshots
├── udify.sqlite3                git-ignored — local audit/workflow DB
│
├── governance/                  rule book, planning docs, session logs
│   ├── RULEBOOK.md, BOOTSTRAP.md, AGENTS.md-at-root
│   ├── planning/                PLAN, DB-DESIGN, IMPL-SPEC, UI-SPEC,
│   │                            TODO, DISCOVERY, SECURITY, RELEASE-PLAN
│   │                            + UDIFY-SPECIFICATIONS.md (master spec)
│   ├── ai-context/              SESSION-*.md (latest 3 kept, older archived)
│   ├── work-log/                LOG-*.md (plain language, one per day)
│   └── documentation/           SETUP-GUIDE.md
│
├── Scratch/                     git-ignored — disposable prep only, never
│   │                            continuity records and never production code
│   └── UdiFy/coding/            the UI prototype from the UI DESIGN phase
│
└── UDISE/                       git-ignored — the 9 source screen recordings
                                 (167 MB, local only by user decision)
```

### Deliberate gaps and absences in this tree

- **No `pyproject.toml`** — `requirements.txt` + `pytest.ini` is what the
  project actually uses; a pyproject would be a second, competing source of
  truth for dependencies and tool config.
- **No packaging directory** — `installer.spec` / `installer.iss` and all
  build output were removed 2026-09-27 at the user's request. Smart App
  Control blocks unsigned `.exe` files on the target machine, so no
  packaging target could produce a launchable binary, and installing one
  overwrote the working `pythonw.exe` launcher. Do not reintroduce without
  solving code signing first.
- **`tests/live/` is empty** — the L1/L2/L3 live-verification evidence was
  produced by throwaway scripts that were never committed, so it is not
  reproducible. This is a real gap, not an oversight: the folder is
  reserved and named so the next person knows where committed live
  verification scripts belong.
- **`udify.sqlite3` sits at ROOT**, not under a `data/` folder. A `data/`
  layout was briefly added to serve the (now-removed) installer and was
  reverted; `UDIFY_SQLITE_PATH` in `.env` can point it anywhere if that
  changes.

This tree is recorded so IMPL-SPEC.md and future sessions can reference
exact paths. It is a *description of reality*, not a proposal — if it and
the code ever disagree, the code wins and this section must be corrected.

## Progress rules

- Do not reprocess a GREEN row by default (spec §AG/§264/§89).
- Do not run ND reconciliation automatically as part of ordinary batch
  processing — it is a separate, explicitly triggered operation (spec §V,
  §136).
- Transfer-request/approval status checks are always batched with a single
  up-front operator confirmation, never per-student (spec §M).
- Any unknown portal state halts that student's processing and requires
  manual review; it never stops other independent students unless
  continuing would risk incorrect government data (spec §T, §AI.22-23).

## Sample outputs

- A completed UDISE row: entire row GREEN, `UDISE No` populated with the
  real 18-digit value (spec §6/§80).
- A completed New-PEN row: `PEN = ND`, entire row GREEN (spec §54/§81,
  §128.3) — this is success, not failure.
- A pending Import row: LIGHT ORANGE, remark `IMPORT PENDING` (spec §296).
- An active transfer request: LIGHT ORANGE, remark `REQUEST SENT` — never
  renamed to `IMPORT PENDING` (spec §K).
- Approval-history export: filtered XLSX/CSV respecting active filters
  (spec §O).

## What this plan deliberately does not repeat

Field-by-field UDISE/PEN form layouts, exact button labels, and portal
screen sequences are NOT duplicated here — they live in UI-SPEC.md
(organized) and the master spec (full detail, e.g. §163-164, §W-§Y). This
avoids the workspace holding duplicate/divergent copies of the same
requirement (RULEBOOK.md §B/§H.4).
