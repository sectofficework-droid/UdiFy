# BOOTSTRAP.md — UdiFy Current State

> Read this every session (RULEBOOK.md §0/§C.2 — ALWAYS). Curated snapshot,
> not an archive — see RULEBOOK.md §D size-discipline rule.

## Current state (as of 2026-09-25, session 1)

- **Mode**: NEW project (RULEBOOK.md §0 activation — no code/git existed
  when RULEBOOK.md was found at ROOT this session).
- **Phase**: CODING (UI DESIGN CONFIRMED closed + CODING opened — user
  said **"code it"** 2026-09-25; per RULEBOOK.md §F's trigger-alias logic,
  "code it"/"start backend" close the UI gate and open CODING together).
- **Gate**: CODING open. Implementing mechanically from IMPL-SPEC.md +
  TODO.md's mock-first build order; no improvisation on business rules.
- **Approvals given**: git init; secrets approach; stack lock-in (bundled
  clarify round, 2026-09-25). **PLANNING approved** ("approve plan").
  **DESIGN FIXED approved** ("approve design"). **UI DESIGN CONFIRMED
  closed + CODING opened** ("code it").
- **Approvals pending**: run tests / approve release.

## Real environment versions (verified this session, §A.8/§C.2)

- Python: **3.14.7** (`C:\Python314\python.exe`) — via `python --version`.
- Git: **2.55.0.windows.3** — via `git --version`.
- OS: Windows 11 Home Single Language 10.0.26200.
- No Node.js dependency in this project (Node was only used transiently by
  the AI session itself to slice RULEBOOK.md text — not a project
  dependency).
- Playwright/PySide6/etc. versions: not yet installed — TBD at CODING.

## What exists on disk right now

```
D:\Project\UdiFy\
├── AGENTS.md                              (created this session)
├── .gitignore                             (created this session)
├── governance\
│   ├── RULEBOOK.md                        (moved from ROOT this session)
│   ├── BOOTSTRAP.md                       (this file)
│   ├── ai-context\SESSION-2026-09-25-1.md
│   ├── work-log\LOG-2026-09-25.md
│   ├── planning\
│   │   ├── UDIFY-SPECIFICATIONS.md        (moved from ROOT this session — MASTER SPEC, source of truth)
│   │   ├── DISCOVERY.md
│   │   ├── PLAN.md
│   │   ├── DB-DESIGN.md
│   │   ├── IMPL-SPEC.md
│   │   ├── UI-SPEC.md
│   │   ├── TODO.md
│   │   ├── SECURITY-THREAT-MODEL.md
│   │   └── RELEASE-PLAN.md
│   └── documentation\SETUP-GUIDE.md
└── Scratch\UdiFy\coding\{assets\{css,js,img}}, debugging\, suggestions\  (empty stubs, git-ignored)
```

No production code exists yet — correct for PLANNING phase (RULEBOOK.md
§A.1/§H.1).

## Git state

- Repo initialized this session (`git init`); remote `origin` =
  `https://github.com/sectofficework-droid/UdiFy.git`.
- Git identity configured by the user themselves (not by the AI session —
  updating git config is an absolute "never" for this session):
  `bkdebiprasaddas-blip <bkdebiprasaddas@gmail.com>`.
- **Committed and pushed** — user said "push" (with nothing committed yet,
  the only sensible reading was commit-then-push); root commit `66faf93`
  on `master`, tracking `origin/master`. 43 files, the full governance
  scaffold + build-order steps 1-4 (config/DB/Sheets adapter/diagnostics).
- `.gitignore` confirmed to exclude `Scratch/`, `.env*`, `credentials/`,
  `*.sqlite3`, build artifacts, etc. — verified `Scratch/` does not even
  appear in `git status --short` output.
- Secret scan: performed on all `governance/` content before staging (see
  SESSION-2026-09-25-1.md) — no secrets found (project contains no
  credentials yet; none were pasted into any doc).

## Assumptions on record (user may veto per RULEBOOK.md §C2.3)

- Aadhaar-consent automation stays manual-only by default until the school
  explicitly authorizes otherwise (DISCOVERY.md open question 3).

## Open questions (not blocking PLANNING, needed before later gates)

1. Numeric MVP success metrics — needed before RELEASE.
2. **Resolved 2026-09-25**: Google Cloud project/service account and
   government-portal credentials — explicit decision made to proceed
   **mock-first**. Neither is needed to start or continue CODING; see the
   master spec's "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION",
   TODO.md's mock-first build order + Live Verification Gate, and
   RELEASE-PLAN.md's updated "Test target". Real credentials are supplied
   later, only for the separate Live Verification Gate phase.
3. Aadhaar-consent automation: confirm manual-only, or authorize automation?
4. **Resolved 2026-09-25**: PEN Import's ACTIVE/pending outcome, PEN
   Request Sent (Student Release Request generation), and View Sent
   Request (National status monitoring) — user re-checked all three
   recordings directly and supplied the full workflows (now in
   UDIFY-SPECIFICATIONS.md). Every stale "not yet documented" statement in
   the spec was replaced outright, not just annotated — see the spec's
   own "FINAL DOCUMENTATION CLASSIFICATION" block for the authoritative
   per-workflow status. **Still open**: the successful/Dropbox outcome for
   UDISE Import and PEN Import (neither demonstrated by any recording, and
   the spec explicitly warns not to infer it from the ACTIVE-outcome
   workflows) — see UI-SPEC.md §B.5 for the current coverage table.

## Next trigger

**CODING's mock-first build order is complete (2026-09-25, TODO.md steps
1-16)** — all four entry conditions, PEN Request Sent/View Sent Request,
ND Reconciliation, the cross-portal approval batch flow, a generic
session/timeout/crash recovery layer, a dedicated UI-change resilience
test pass, the full PySide6 GUI (wired to the real engine, not mocked
views), and PyInstaller packaging (verified by actually launching the
built `.exe`). 60/60 tests passing. Stopped at the Live Verification Gate
(step 17) — see TODO.md's "Live Verification Gate" section for the exact
report template and status, and TODO.md's testing matrix/acceptance
criteria for an honest, item-by-item account of what remains open (a few
things do: automated Condition 1-4 routing from sheet state, checkpoint-
based resume-after-interruption, and the "successful/Dropbox" outcome for
either portal's Import workflow — all explicitly marked, none silently
skipped).

Say **"run tests" / "test it"** to formally close the TESTING gate, or
supply real credentials to begin the Live Verification Gate's L1-L4
phases.
