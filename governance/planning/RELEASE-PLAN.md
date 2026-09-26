# RELEASE-PLAN.md — UdiFy

> Per RULEBOOK.md §E.8. Required before "approve release". This is a
> forward-looking skeleton written during PLANNING — most fields are
> **TBD** until CODING/TESTING produce real evidence to fill them in.
> Do not treat any TBD below as filled just because this file exists.

## Environments

- **Development**: the school's (or developer's) local Windows machine,
  Python 3.14.7 confirmed installed (see BOOTSTRAP.md). No staging/cloud
  environment — this is a local desktop app (spec §AD).
- **Production**: the school's operating Windows machine(s) where staff run
  the packaged `.exe`. Same machine class as development; no separate
  staging tier is specified by the source material. **Confirmed
  2026-09-26**: this project's development machine (Lenovo 83DV, Windows
  11 Home Single Language, build 26200) IS the same machine the school
  uses for its actual UDISE portal operations — there is no separate
  target machine to additionally verify against. See "Smoke tests" and
  release-criteria item 3 below.
- **Test target: resolved 2026-09-25 — mock-first.** The bulk of TESTING
  (state machine, adapters, idempotency, recovery, selector fallback,
  audit trail, GUI) runs entirely against `MockSheetsRepository` and
  mocked/fixture portal pages — see TODO.md's mock scenario checklist and
  the master spec's "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION"
  for the full required scenario list. Real Google Sheets/portal
  credentials are needed only for the separate **Live Verification Gate**
  (TODO.md: phases L1 Authentication → L2 Read-only → L3 Controlled
  student → L4 Recovery, using one specifically authorized test student —
  never the school's live production submissions for exploratory testing,
  RULEBOOK.md §J8/§J0O). This resolves what was previously an open
  question about whether a safe test student record exists on the real
  portals — it's deferred to the Live Verification Gate, not needed
  before or during CODING.

## Build

- Packaging: PyInstaller → Windows one-folder build (spec §AE/§76) — done
  2026-09-25 (TODO.md step 16). `installer.spec` at the repo root; build
  with `pyinstaller installer.spec` from an activated venv. Entry point
  is `run_udify.py` (thin wrapper around `src.app.main.main()`). Output
  is `dist/UdiFy/` (an `UdiFy.exe` plus an `_internal/` support folder).
- **Superseded 2026-09-26 — the packaged `.exe` does not run on the
  actual target machine.** Rebuilding the same spec with current code
  and launching the fresh `dist/UdiFy/UdiFy.exe` (both directly and via
  a Start Menu shortcut) failed with "An Application Control policy has
  blocked this file" — a Windows security policy on this machine blocks
  unsigned/unrecognized executables, and a PyInstaller build has no code
  signature without a certificate (real cost/process, out of scope now).
  **Working alternative, verified**: launch from source via
  `.venv\Scripts\pythonw.exe run_udify.py` (windowless — `pythonw.exe`
  is already trusted by the policy) — a Start Menu shortcut (`UdiFy.lnk`)
  now does exactly this. Deployment on this machine (and presumably any
  machine under the same policy) therefore means keeping the project
  source + `.venv` in place and launching via that shortcut, **not**
  copying and running a standalone `.exe`. If a real `.exe` is wanted
  later, it would need code-signing or an Application Control exception
  from whoever manages this policy — neither attempted here.
- **Chromium is not bundled.** The spec bundles Playwright's own driver
  (`playwright.utils.hooks.collect_data_files`) but deliberately does not
  bundle a full Chromium browser build (would add several hundred MB for
  no benefit before Live Verification even runs). The target machine
  needs `playwright install chromium` run once — same requirement as
  development, see SETUP-GUIDE.md.
- The two MOCK fixture pages the GUI's demo dataset drives in MOCK mode
  are bundled as data files (`fixtures/gujarat_udise/new_entry.html`,
  `fixtures/udise_plus/new_pen_entry.html`) so the packaged app's Batch
  Queue/ND Reconciliation/Approval Monitoring screens keep working
  out of the box; `src/app/mock_fixtures.py` resolves their path via
  `sys._MEIPASS` when frozen, the source tree's `tests/fixtures/` path
  otherwise.
- Dependency pinning: `requirements.txt`, exact versions (done at CODING
  setup, TODO.md step 1).
- Build reproducibility / artifact identification (RULEBOOK.md §J15G/§J16):
  TBD — recommend embedding a build/version identifier the diagnostics
  system can report (spec §H "automation build/version").

## Migrations

- No relational schema migrations in the traditional sense beyond the
  local SQLite DB (DB-DESIGN.md §B). Recommend a lightweight versioned
  schema/migration approach for SQLite (e.g. a `schema_version` table +
  ordered migration scripts) so future changes to `pen_case_events` or
  other tables don't silently break existing installs — decided at CODING
  time.
- No migration path exists yet because no schema has been created yet.

## Secrets / config

- Google service-account JSON + government portal login config: local
  `.env` + git-ignored `credentials/` folder (confirmed decision,
  2026-09-25 — see BOOTSTRAP.md).
- `.env.example` (trackable template, no real values) to be created at
  CODING time so setup is reproducible without exposing secrets.
- Google Cloud project / service account provisioning — **resolved
  2026-09-26** (DISCOVERY.md #2): reused the school's existing project
  (`satyam-school-play-publish`), enabled the Sheets API, and created a
  new dedicated `udify-sheets-access` service account (not the project's
  pre-existing `play-publisher` one, which is scoped for Google Play
  Console publishing — unrelated). Key downloaded and imported into
  `credentials/service-account.json`. All 3 real spreadsheets (OGR/
  UDISE/PEN, identified by user-supplied links and content-verified
  before sharing) shared with the service account's email, IDs recorded
  in `.env`. Only the two government portal logins remain to configure.

## Monitoring

No hosted/cloud monitoring applies (local desktop app). Observability is
local: the structured logging + diagnostics system (RULEBOOK.md §L,
IMPL-SPEC.md "Diagnostics on failure") is the operational monitoring
mechanism — an operator reviewing the Diagnostics view (UI-SPEC.md §B.1)
after a run is the intended incident-detection path. No alerting/paging is
specified or needed for a single-operator local tool.

## Backups

- **Google Sheets (OGR/UDISE/PEN)**: these are the school's own documents;
  Google Sheets version history provides some inherent recovery, but this
  project does not manage that backup — recommend confirming the school
  has its own backup/versioning discipline for these sheets (open item, not
  this application's responsibility to implement).
- **Local SQLite audit DB**: no backup mechanism specified. Given it holds
  the immutable audit trail (accountability value), recommend a simple
  periodic local backup/export (e.g. timestamped copy) — TBD, to be
  designed at CODING time, not overbuilt speculatively now.

## Smoke tests (before calling a release usable)

**Mock smoke tests (no credentials needed, runnable throughout CODING):**
- App launches, connects to `MockSheetsRepository`, reads all three mock
  workbooks without error. **Verified 2026-09-26 on the confirmed target
  machine** (the school's own UDISE-operations machine, not a separate
  developer machine — see "Environments" above): the real entry point's
  theme + `MainWindow` + `AppContext` were launched together (not just
  constructed, as `tests/unit/test_app_smoke.py` does), the Batch Queue
  screen rendered with the navy/orange theme applied and the 5-student
  MOCK dataset populated (screenshotted).
- One full Condition-1 (New/New) run against mocked portal pages
  completes end-to-end with correct GREEN/ND results, `environment =
  MOCK` throughout, and no write anywhere marked `LIVE_VERIFIED_SUCCESS`.
  **Verified 2026-09-26 on the target machine**: ran through the actual
  Run & Progress screen (clicking Start run, not calling the engine
  directly), the real `RunWorker` background thread opened a real
  visible Playwright browser against the MOCK fixtures, and the run
  reached `PEN_RESOLVED`/`RESOLVED`, both sheet rows GREEN, PEN=`ND`
  (screenshotted).
- `AUTOMATION_PAUSED_FOR_USER` prompt (e.g. simulated Aadhaar consent
  step) appears and resumes correctly against the mock. **Not
  re-verified through the GUI this pass** — the MOCK demo dataset's
  fixture URL doesn't trigger the consent branch, and forcing it would
  mean changing app code just to manufacture a demo scenario. Covered by
  `tests/integration/test_national_udise_adapter.py`'s
  `test_aadhaar_consent_pauses_and_is_never_auto_clicked`, which does run
  on this same now-confirmed target machine as part of the automated
  suite (102/102 passing here).
- Diagnostics capture works when a failure is deliberately induced (spec
  §L10-equivalent test for this app). **Not re-verified through the GUI
  this pass** (no failure was induced in the live run — the Diagnostics
  screen correctly showed empty) — covered by
  `tests/unit/test_diagnostics.py`'s deliberately-triggered-failure test,
  also running on this machine as part of the same 102/102 pass.

**Live smoke tests (only at the Live Verification Gate, TODO.md, once
real credentials are configured):**
- App launches, connects to the real Google Sheets, reads all three real
  workbooks without error.
- Playwright opens a visible browser and reaches both real portal login
  pages (Live Verification phase L1).
- One full Condition-1 run against a designated, specifically authorized
  safe test student completes end-to-end with correct GREEN/ND results,
  verified against the actual portal state, `environment = LIVE`,
  case status `LIVE_VERIFIED_SUCCESS` — not just "no exception thrown"
  (RULEBOOK.md §J13; Live Verification phase L3).

## Deployment steps

**Resolved 2026-09-26** — not the originally-expected "copy the packaged
`.exe`" path, since that's blocked on this machine (see "Build" above).
The actual, verified steps on this machine:

1. Project source + `.venv` live at `D:\Project\UdiFy` (already the
   case — this machine is both the development and the school's actual
   UDISE-operations machine, per "Environments" above).
2. `.env`/`credentials/service-account.json` populated (via the app's
   own Settings screen or by hand) — already done for Google Sheets,
   government portal logins still pending as of this writing.
3. Start Menu shortcut `UdiFy.lnk` (created 2026-09-26) launches
   `.venv\Scripts\pythonw.exe run_udify.py` with the project directory
   as its working directory — this is what "launch UdiFy" means on this
   machine going forward, not double-clicking a `.exe`.

If UdiFy is ever deployed to a *different* machine, re-verify whether
that machine has the same Application Control restriction before
assuming either distribution path works — don't assume the `.exe` is
safe to try again without checking first.

**2026-09-26, at user request**: also built a single-file variant
(`installer-onefile.spec`, tracked in git; `pyinstaller installer-
onefile.spec`) and placed the resulting `UdiFy.exe` (~110MB) at the
repo root — untracked/git-ignored (`/UdiFy.exe` in `.gitignore`), for
the user to install/allow themselves. Confirmed it hits the exact same
Application Control block as the one-folder build (expected — the block
is about the missing code signature, not the packaging format). The
specific Windows feature involved is **Smart App Control** (`Get-
MpComputerStatus`'s `SmartAppControlState: On`) — a consumer Windows 11
setting the user could disable via Windows Security → App & browser
control, but that's a one-way switch (cannot be re-enabled without
reinstalling Windows) and a system-security-setting change, so left
entirely to the user's own decision and action, never done by this
session.

## Rollback path (recorded 2026-09-26, RELEASE gate remediation item 4)

Since this is a new local install with no prior production version,
"rollback" has two parts:

1. **Build rollback.** Keep the previous working `dist/UdiFy/` folder
   (the whole folder, not just the `.exe` — see "Build" above) archived
   under a version-labeled path (e.g. `releases/UdiFy-<date-or-tag>/`)
   before overwriting it with a new build. If a new build misbehaves on
   the school's machine, restore the previous folder and relaunch — no
   installer/uninstaller step exists to reverse, since this is a
   one-folder copy, not an installed application.
2. **Operational rollback.** If the tool itself must be pulled entirely
   (not just rolled back a version) — e.g. a MOCK/LIVE mixing bug, or an
   automation error discovered against the real portals — the fallback
   is manual entry: the school's staff continue entering UDISE/PEN data
   directly on the government portals as they did before this project
   existed. Nothing about this tool's design blocks that fallback (spec
   §AF: the OGR/UDISE/PEN Google Sheets remain the source of truth, never
   this tool's local SQLite state), so no data migration or cleanup step
   is needed to revert to manual operation — simply stop running the
   tool. `pen_case_events`/`request_cases` rows already recorded stay as
   an audit trail of what the tool did before being pulled; they don't
   need to be undone.

No numbered release has shipped yet, so there is no prior version to
name here — this section records the *procedure*, to be followed from
the first real release onward.

## Release criteria (gate for "approve release")

- [ ] All TESTING-phase acceptance criteria (TODO.md) pass with evidence.
- [x] SECURITY-THREAT-MODEL.md open questions answered or explicitly
      accepted as risk by the school (RULEBOOK.md §J0E exception process
      if any is knowingly deferred) — **closed 2026-09-26**: data
      retention (kept indefinitely, no school policy), encryption at rest
      (OS-level protection is sufficient, no school requirement),
      Aadhaar-consent-always-manual (confirmed, no exceptions), and no-
      secrets-in-git-history (verified) — see SECURITY-THREAT-MODEL.md's
      "Verification before RELEASE gate" and "Data handling" sections.
- [x] Smoke tests above pass on the actual target machine, not only a
      developer machine — **closed 2026-09-26**: confirmed this project's
      machine IS the school's UDISE-operations machine (see
      "Environments" above), then re-ran the MOCK smoke tests through the
      real GUI entry point on it (see "Smoke tests" above for exactly
      what was and wasn't re-verified through the GUI vs. covered by the
      automated suite already running on this machine).
- [x] Rollback path confirmed — **closed 2026-09-26**, see "Rollback
      path" above.
- [x] BOOTSTRAP.md and this file both reflect the real, verified state (no
      stale TBDs presented as done) — **closed 2026-09-26**: BOOTSTRAP.md
      was fully refreshed (it was frozen at 2026-09-25 session 1, still
      claiming Playwright/PySide6 "not yet installed" and "60/60 tests"
      — both stale). This file's own remaining TBDs (build-version
      stamping, SQLite backup/export, formal deployment steps) are left
      as genuine TBDs, not falsely closed — none are load-bearing for
      "approve release" itself.
