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

**Bug found and fixed the same day**: the packaged app rendered an empty
window (both builds) even once launchable — `src/config/settings.py`'s
`PROJECT_ROOT = Path(__file__).resolve().parents[2]` doesn't work once
frozen (`__file__` for a module loaded from PyInstaller's bundle isn't a
real on-disk path), so the SQLite DB/diagnostics/`.env` all resolved to
somewhere bogus. `src/app/mock_fixtures.py` already had the correct
`sys._MEIPASS`-based workaround for exactly this problem for fixture
files; `settings.py` was just never updated to match. Fixed to use
`sys.frozen`/`sys.executable`'s directory when frozen (commit `9a929fd`)
— confirmed working by rebuilding and having the user check the running
window directly.

**Proper installer added 2026-09-26, at user request**: `installer.iss`
(Inno Setup — installed via `winget install JRSoftware.InnoSetup` with
the user's explicit OK first, since installing new software is a real
system change) builds `UdiFy-Setup.exe`, a real Windows installer with
Start Menu entry, optional desktop shortcut, and an uninstaller
(`unins000.exe`) registered like any normal Windows program. Installs
to `%LOCALAPPDATA%\Programs\UdiFy` — a per-user location needing no
admin rights/UAC prompt, chosen deliberately over Program Files so the
app can actually write its own SQLite DB/diagnostics next to itself
without a permissions problem (Program Files is not user-writable
without elevation). Build with `pyinstaller installer-onefile.spec`
then `ISCC.exe installer.iss` (path: `%LOCALAPPDATA%\Programs\Inno
Setup 6\ISCC.exe`); output `dist_installer\UdiFy-Setup.exe` is
git-ignored, same as other build artifacts — `installer.iss` itself is
tracked. **Verified end-to-end**, not just "compiles": ran a real
silent install to a throwaway directory (`/DIR=` override, never the
real target), launched the installed copy, confirmed `udify.sqlite3`
and `diagnostics/` were created correctly inside the install folder
(the exact bug just fixed above), then ran the generated uninstaller
and confirmed full removal.

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

- [x] All TESTING-phase acceptance criteria (TODO.md) pass with evidence.
      **Closed 2026-09-27 under an accepted exception (EX-2026-09-27-01),
      not unconditionally** — full suite re-run and confirmed **110/110
      passing** (0 skipped, 136s) at the time of approval. Every acceptance
      criterion that is actually implemented is checked and passing. The
      three known-unbuilt retry/recovery flows (save-succeeded-but-unconfirmed
      retry, sheet-write-failure-after-portal-success recovery, full
      mid-branch resume for the National UDISE+ multi-tab profile fill) were
      **knowingly released without**, per the user's explicit decision. See
      "Accepted exceptions" below for the full risk record, and TODO.md's
      testing matrix for the exact per-item status, which stays open and
      honest rather than being ticked off.
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

## Accepted exceptions (RULEBOOK.md §J0E)

### EX-2026-09-27-01 — Release approved with unverified live-portal navigation

| Field | Value |
| --- | --- |
| **Exception ID** | EX-2026-09-27-01 |
| **Affected requirement** | RELEASE-PLAN.md release criterion 1 (all TESTING acceptance criteria pass with evidence) |
| **Reason** | The National UDISE+ "Add Student" / identity-confirm flow was rebuilt from the project's own screen recordings and has **never run against the real portal** — the live session was paused at the user's instigation (repeat-login account-lockout risk). Live Verification Gate L3 has never completed. The three unbuilt retry/recovery flows in TODO.md's testing matrix would require inventing portal navigation no recording confirms (RULEBOOK.md §J14) to do honestly. |
| **Scope** | The National UDISE+ New-PEN branch only: `open_add_student()`, `fill_identity_fields()`, `read_identity_confirmation()`, `confirm_identity_details()`. The Gujarat UDISE branch, ND reconciliation, manual review, duplicate-request guards and checkpoint/resume are **not** in scope of this exception — they are unchanged from what was already tested. |
| **Risk** | If the rebuilt selectors are wrong, the New-PEN branch fails against the real portal. Mitigating: it fails **loudly** (timeout/strict-mode violation), not silently; no sheet is marked GREEN without the spec's full verification sequence, so a wrong selector cannot corrupt the register; the duplicate-request guard means a retry cannot create a second entry. Residual risk accepted: a mid-run interruption during the National multi-tab profile fill routes to manual review rather than resuming, so an operator may need to complete one entry by hand. |
| **Mitigation** | ~~`UDIFY_ENVIRONMENT` **stays `MOCK`** — the user's explicit decision on approval.~~ **SUPERSEDED 2026-09-27 — see EX-2026-09-27-02.** As originally approved, LIVE mode was a separate, manual `.env` edit that the user would make deliberately, and no live portal automation would be run without their per-run go-ahead. Rollback path recorded above (fall back to manual portal entry; nothing blocks it) is unaffected and remains the primary safety net. |
| **Owner** | Human project owner (school). |
| **Approved by** | User, explicit **"approve release"** + "Approve, but keep LIVE off", 2026-09-27. Agent may recommend but cannot self-approve (§J0.12). |
| **Start date** | 2026-09-27 |
| **Review / expiry** | Review at Live Verification Gate L3, or immediately on any real-DOM mismatch in the New-PEN flow. **NOW ACTIVE (load-bearing) as of 2026-09-27** — see EX-2026-09-27-02: the mitigation that kept this risk dormant has been withdrawn by the user, so this exception is live rather than hypothetical. |

### EX-2026-09-27-02 — User withdrew the LIVE-off mitigation; LIVE is now on

| Field | Value |
| --- | --- |
| **Exception ID** | EX-2026-09-27-02 |
| **Affected requirement** | The mitigation recorded in EX-2026-09-27-01; and RELEASE-PLAN.md release criterion 1, which is now satisfied **only** by this exception and EX-2026-09-27-01 together. |
| **Reason** | On 2026-09-27, immediately after approving release with LIVE off, the user directed **"make everything live"** — i.e. to authorise operation against the real government portals and the real OGR/UDISE/PEN registers without waiting for further per-run sign-off. **This materially widens the risk EX-2026-09-27-01 was recorded against, and is recorded here as such rather than folded silently into the original exception.** Verified during this session: `.env` already had `UDIFY_ENVIRONMENT=LIVE` (set earlier, on 2026-09-26, for the Live Verification Gate), so the standing instruction that UdiFy **must not** write to the real registers until further notice is now **withdrawn** — it was being enforced in practice only by the app not being run. |
| **Scope** | The whole application, in LIVE mode, against **both** real portals and all three real spreadsheets. This is broader than EX-2026-09-27-01, whose scope was the National UDISE+ New-PEN branch alone. |
| **Risk** | **(a)** The National UDISE+ New-PEN branch (Add Student → identity fields → identity-confirm modal) is still **entirely video-inferred and has never been exercised against the real DOM**; the precise cell-click fix in `open_add_student()` is likewise unverified. A wrong selector fails loudly, not silently, and cannot mark a row GREEN without the spec's full verification sequence — but a run may still need to be abandoned partway. **(b)** L2 has **never been run against the Gujarat (state) portal** — only its login was ever live-checked; the UDISE side of every condition is effectively unverified live. **(c)** L3 has never completed, so no end-to-end LIVE run has ever been proven. **(d)** Mid-run interruption during the National multi-tab profile fill routes to manual review rather than resuming — an operator may need to finish one entry by hand. **(e)** With no per-run sign-off, an unattended or mistaken batch run could submit real entries against a real government account; the duplicate-request guard prevents duplicate *requests* and duplicate *new* entries after an interrupted attempt, but it cannot prevent a wrong-but-valid submission. |
| **Mitigation** | What still holds, and is the reason this is an exception rather than a stop: the spec's consequential-action verification rule is structurally enforced (nothing is recorded GREEN or `LIVE_VERIFIED_SUCCESS` without locate → verify identity → verify state → act → verify result → record), so a failed or mis-targeted run degrades to a loud, logged, diagnosable stop rather than silent corruption; the operational rollback (revert to manual portal entry) is unaffected and requires no data migration; and a single operator is present at the machine for any live run. **Withdrawn by this exception:** the MOCK default, and the per-run go-ahead requirement. |
| **Owner** | Human project owner (school). |
| **Approved by** | User, explicit **"make everything live"**, 2026-09-27. Agent may recommend but cannot self-approve (§J0.12); the agent additionally flags the unverified scope above rather than treating the directive as risk-free. |
| **Start date** | 2026-09-27 |
| **Review / expiry** | **Recommend review after the first successful L2 (Gujarat read-only) and the first L3 controlled-student run** — both are the cheapest points at which real evidence can retire (a) and (b). Until then, treat every live run as exploratory: one student, supervised, with the Diagnostics view open. Re-verify at each session start, per RULEBOOK.md §J0G (evidence freshness) — the unverified-selector risk is invalidated by any change to `src/portals/**`. |

## Release approval (recorded 2026-09-27)

**RELEASE gate: APPROVED**, with **EX-2026-09-27-01 and EX-2026-09-27-02** on record. All five release criteria above are closed — four unconditionally, one under the two recorded exceptions.

**What this approval authorises.** For this application "release" uniquely means *the tool is allowed to operate against real government portals and real school spreadsheets*.

- **As first approved (2026-09-27, morning):** approved with `UDIFY_ENVIRONMENT` remaining `MOCK` — a MOCK-mode release, with LIVE activation as a separate, explicitly-approved future step.
- **As amended (2026-09-27, later — "make everything live"):** **LIVE operation is authorised**, in the full sense — both real portals and all three real registers — **without waiting for per-run sign-off**. This supersedes the LIVE-off scope above.

**This is a material widening of the release's risk, recorded deliberately.** The application has never completed a single end-to-end live run: L3 has never succeeded, the National New-PEN selectors have never touched the real DOM, and the Gujarat portal has never been read live at all. The user is the owner and has directed this; per RULEBOOK.md §J0U that is their call to make, and per §J0E it is recorded as an accepted exception with a review date rather than silently absorbed. What the agent will not do is describe the LIVE path as verified.

**Live smoke tests remain unrun** (see "Smoke tests" above — all three). They are not waived by this approval; they remain the outstanding verification work tracked in TODO.md, and are now the recommended first priority precisely because LIVE is on.
