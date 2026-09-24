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
| Packaging | PyInstaller (.exe) | §AE, §76 |

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

```
UdiFy/
├── AGENTS.md
├── .gitignore
├── governance/                  (this scaffold)
├── src/
│   ├── app/                     PySide6 UI entry point + windows/dialogs
│   ├── engine/                  workflow/state engine, condition routing
│   ├── sheets/                  Google Sheets adapter, normalization
│   ├── portals/
│   │   ├── udise_gujarat/       Gujarat UDISE page objects/adapters
│   │   └── udise_plus/          National UDISE+ page objects/adapters
│   ├── db/                      SQLite schema, migrations, DAO layer
│   ├── diagnostics/             structured logging, screenshot capture
│   └── config/                  routing tables, selector config (not secrets)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                mocked/stubbed portal pages
├── credentials/                 git-ignored — service account JSON, .env
└── requirements.txt / pyproject.toml
```

This tree is not created until the CODING gate ("code it") per RULEBOOK.md
§F; it is recorded here so IMPL-SPEC.md can reference exact paths.

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
