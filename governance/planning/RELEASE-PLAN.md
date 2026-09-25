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
  staging tier is specified by the source material.
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
  is `dist/UdiFy/` (an `UdiFy.exe` plus an `_internal/` support folder) —
  copy the whole folder, not just the `.exe`, to the target machine.
  Verified by actually launching the built `.exe` (not just running the
  build step) and confirming the GUI renders and its SQLite/diagnostics
  files are created correctly.
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
- Google Cloud project / service account provisioning: **open question**
  (DISCOVERY.md #2) — does the school already have one, or does this need
  to be created?

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
  workbooks without error.
- One full Condition-1 (New/New) run against mocked portal pages
  completes end-to-end with correct GREEN/ND results, `environment =
  MOCK` throughout, and no write anywhere marked `LIVE_VERIFIED_SUCCESS`.
- `AUTOMATION_PAUSED_FOR_USER` prompt (e.g. simulated Aadhaar consent
  step) appears and resumes correctly against the mock.
- Diagnostics capture works when a failure is deliberately induced (spec
  §L10-equivalent test for this app).

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

TBD — expected to be "copy the packaged `.exe` + config template to the
school machine, populate `.env`/`credentials/` locally, run." No CI/CD
pipeline, container, or cloud deployment is in scope (single local
desktop app). Formalize exact steps once packaging (TODO.md build-order
step 15) exists.

## Release criteria (gate for "approve release")

- [ ] All TESTING-phase acceptance criteria (TODO.md) pass with evidence.
- [ ] SECURITY-THREAT-MODEL.md open questions answered or explicitly
      accepted as risk by the school (RULEBOOK.md §J0E exception process
      if any is knowingly deferred).
- [ ] Smoke tests above pass on the actual target machine, not only a
      developer machine.
- [ ] Rollback path confirmed: since this is a new local install with no
      prior production version, "rollback" means keeping the previous
      working `.exe` build available and being able to revert to manual
      entry if the tool must be pulled — record this explicitly once a
      first release exists.
- [ ] BOOTSTRAP.md and this file both reflect the real, verified state (no
      stale TBDs presented as done).
