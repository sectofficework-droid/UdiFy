# BOOTSTRAP.md — UdiFy Current State

> Read this every session (RULEBOOK.md §0/§C.2 — ALWAYS). Curated snapshot,
> not an archive — see RULEBOOK.md §D size-discipline rule.

## Current state (as of 2026-09-26, session 2)

- **Mode**: Established project — mock-first build complete, past CODING.
- **Phase**: TESTING gate **closed** ("test it", 2026-09-26). RELEASE gate
  remediation largely complete; **not yet approved** — 2 open items
  remain (below), both needing the user's answer/action, not code.
- **Gate**: Awaiting **"approve release"** (again — the first time it was
  said, 2026-09-26, real unmet checklist items were surfaced instead of
  silently closing the gate; most have since been resolved).
- **Approvals given**: git init; secrets approach; stack lock-in.
  **PLANNING approved**. **DESIGN FIXED approved**. **UI DESIGN CONFIRMED
  closed + CODING opened** ("code it"). **TESTING closed** ("test it").
- **Approvals pending**: approve release.
- **Tests**: 110/110 passing (`pytest -q`), as of commit `59a92f3`.
- **Git**: local `master` is 4 commits ahead of `origin/master` (not
  pushed this session — only push when the user asks).

## Real environment versions (this machine — confirmed 2026-09-26 to BE
the school's actual UDISE-operations machine, not a separate dev box)

- Python: **3.14.7** (`.venv` at repo root) — via `python --version`.
- Git: **2.55.0.windows.3** — via `git --version`.
- OS: Windows 11 Home Single Language, build 26200. Lenovo 83DV.
- Playwright: **1.63.0** (installed; Chromium confirmed present —
  every adapter/GUI test launches a real, visible browser).
- PySide6: **6.11.2** (installed; real GUI launched and screenshotted
  this session, navy/orange theme confirmed rendering correctly).
- No Node.js dependency in this project.
- **Application Control policy blocks unsigned `.exe` files** —
  discovered 2026-09-26: a freshly PyInstaller-built `dist/UdiFy/
  UdiFy.exe` refuses to launch here ("An Application Control policy has
  blocked this file"), both directly and via a Start Menu shortcut.
  `.venv\Scripts\pythonw.exe run_udify.py` (source, windowless) launches
  the identical app fine — `pythonw.exe` is a trusted, signed binary the
  policy allows. **Implication for future sessions**: don't assume a
  PyInstaller build is launchable here just because `pyinstaller` exits
  0 — verify by actually launching it. The Start Menu shortcut
  `UdiFy.lnk` (points at `pythonw.exe run_udify.py`) is the real,
  working "launch UdiFy" path on this machine. See RELEASE-PLAN.md's
  "Build"/"Deployment steps" for full detail.

## What exists on disk right now

```
D:\Project\UdiFy\
├── AGENTS.md
├── .gitignore
├── .env.example                           (real .env is git-ignored, never committed)
├── requirements.txt, pytest.ini, installer.spec, run_udify.py
├── governance\
│   ├── RULEBOOK.md
│   ├── BOOTSTRAP.md                       (this file)
│   ├── ai-context\, work-log\, archive\
│   ├── planning\
│   │   ├── UDIFY-SPECIFICATIONS.md        (MASTER SPEC, source of truth)
│   │   ├── DISCOVERY.md, PLAN.md, DB-DESIGN.md, IMPL-SPEC.md, UI-SPEC.md
│   │   ├── TODO.md                        (phase gates + build order + honest checklist status)
│   │   ├── SECURITY-THREAT-MODEL.md
│   │   └── RELEASE-PLAN.md
│   └── documentation\SETUP-GUIDE.md
├── src\
│   ├── app\                               (PySide6 GUI: main.py, screens\, theme.py, run_worker.py)
│   ├── config\                            (settings.py, settings_writer.py)
│   ├── db\                                (schema.py + one module per table)
│   ├── diagnostics\                       (logging, redaction, capture)
│   ├── engine\                            (condition1-4.py, branches.py, resilience.py, ...)
│   ├── portals\                           (base.py + udise_gujarat\, udise_plus\ adapters)
│   └── sheets\                            (models.py, repository.py — Mock + real Google impl)
├── tests\ (unit\, integration\, fixtures\) — 110/110 passing
└── credentials\                           (git-ignored, empty until LIVE credentials added)
```

Full mock-first build complete: 4 entry conditions, ND reconciliation,
approval batch flow, manual-review flow, workflow checkpoint/resume,
generic recovery layer, full GUI (including an editable Settings screen
for LIVE credentials, added 2026-09-26), PyInstaller packaging. See
TODO.md for the item-by-item, honestly-marked build order and remaining
gaps — this file stays a snapshot, not a duplicate of that detail.

## Git state

- Remote `origin` = `https://github.com/sectofficework-droid/UdiFy.git`.
- Git identity configured by the user themselves:
  `bkdebiprasaddas-blip <bkdebiprasaddas@gmail.com>`.
- 21 commits on `master`, HEAD `59a92f3`; local is 4 commits ahead of
  `origin/master` (not pushed this session — only push when asked).
- `.gitignore` confirmed to exclude `Scratch/`, `.env*`, `credentials/`,
  `*.sqlite3`, build artifacts, etc.
- Secret scan re-verified 2026-09-26 (SECURITY-THREAT-MODEL.md
  "Verification before RELEASE gate"): full git history checked, only
  `.env.example` (placeholders) was ever added, no real credential ever
  committed, `.env`/`credentials/service-account.json` both confirmed
  git-ignored.

## Assumptions on record (user may veto per RULEBOOK.md §C2.3)

- Aadhaar-consent automation stays manual-only, no exceptions —
  **confirmed by the user 2026-09-26** (DISCOVERY.md open question 3,
  SECURITY-THREAT-MODEL.md).

## Open questions (needed before RELEASE gate)

1. [x] Numeric MVP success metrics — **answered 2026-09-26**: three
      qualitative dimensions (time saved per student, backlog cleared,
      error rate vs. manual entry), no hard numeric targets committed to
      yet — see DISCOVERY.md's "Success metrics" section.
2. [x] Google Cloud project/service account for Sheets API — **resolved
      2026-09-26**: checked directly via console.cloud.google.com — the
      school already had a project (`satyam-school-play-publish`,
      previously used for Google Play Console publishing). Enabled the
      Sheets API on it and created a new, dedicated `udify-sheets-access`
      service account (not the pre-existing `play-publisher` one — kept
      separate for least-privilege). Key downloaded and imported into
      `credentials/service-account.json`, `.env` updated. **Fully
      resolved same day**: all 3 real spreadsheets (user-supplied links,
      content-verified before sharing) shared with `udify-sheets-
      access@satyam-school-play-publish.iam.gserviceaccount.com`, IDs
      recorded in `.env`. Only both portal logins remain to configure.
3. [x] Aadhaar-consent automation — **answered 2026-09-26**: always
      manual, no exceptions, confirming the existing design.
4. [x] PEN Import ACTIVE/pending, PEN Request Sent, View Sent Request —
      resolved 2026-09-25, fully built. **Still open**: the successful/
      Dropbox outcome for UDISE Import and PEN Import (neither
      demonstrated by any recording) — see UI-SPEC.md §B.5.
5. [x] Data retention policy for the local SQLite audit trail —
      **answered 2026-09-26**: none, kept indefinitely.
6. [x] Encryption at rest for the local DB/credentials file — **answered
      2026-09-26**: not required, OS-level protection is sufficient.

## Next trigger

**TESTING gate closed** ("test it", 2026-09-26). RELEASE-gate remediation
mostly complete (workflow checkpoint/resume, new-entry duplicate guard,
target-machine smoke tests, rollback path, all SECURITY-THREAT-MODEL.md
questions, success metrics, GCP provisioning) — see TODO.md's "RELEASE
gate remediation" section for the full item-by-item account. All open
questions above are now answered. What remains before "approve release"
can be honestly recorded is item 1's three still-unbuilt testing-matrix
gaps (checkpoint/resume + retry flows) — or an explicit decision to
release without them.

Say **"approve release"** once that's decided, or supply real
credentials (via the Settings screen or `.env` directly) to begin the
Live Verification Gate's L1-L4 phases — these can proceed independently
of the RELEASE gate itself.
