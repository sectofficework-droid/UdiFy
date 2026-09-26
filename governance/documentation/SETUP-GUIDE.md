# SETUP-GUIDE.md — UdiFy

> Per RULEBOOK.md §E.6. This covers install/run/configure/test/build/
> harden. **Status: current as of 2026-09-25 — every command below has
> actually been run and verified in this session** (RULEBOOK.md §J13),
> not aspirational. The project is mock-first-complete through TODO.md
> step 15; packaging (step 16) is covered below too.

## Prerequisites (confirmed on this machine, 2026-09-25)

- **Python**: 3.14.7 (`C:\Python314\python.exe`).
- **Git**: 2.55.0.windows.3.
- **Playwright Chromium**: required for every mock/live browser
  interaction — install with `playwright install chromium` after
  `pip install -r requirements.txt` (see Install below). Not bundled by
  the PyInstaller build either (see Build).
- **Google Cloud service account / government-portal credentials**: not
  needed to install, build, or run the app in MOCK mode (the default) —
  decision 2026-09-25, "CREDENTIALS, MOCKING AND LIVE VERIFICATION
  DECISION" in the master spec. Configured later, only for the Live
  Verification Gate (TODO.md).

## Install

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

`requirements.txt` pins every dependency to the exact version installed
in this project's `.venv` (PySide6, playwright, google-api-python-client,
openpyxl, pyinstaller, pytest, etc. — RULEBOOK.md §A.8).

## Configure

**Mock mode (default — no real credentials needed):** copy `.env.example`
to `.env`, or run with no `.env` at all — `UDIFY_ENVIRONMENT` defaults to
`MOCK`, and the app runs fully against `MockSheetsRepository` and
fixture-backed portal pages with no further configuration. Useful `.env`
keys (all optional in MOCK mode): `UDIFY_SQLITE_PATH`,
`UDIFY_DIAGNOSTICS_DIR`, `UDIFY_LOG_LEVEL`.

**Live mode (only at the Live Verification Gate, TODO.md):**

Two ways to fill in steps 1-2 below — pick whichever is more convenient:

- **Through the app** (added 2026-09-26): launch UdiFy, open **Settings**,
  browse to the service-account `.json` key (copied into `credentials/`
  automatically) and fill in the three spreadsheet IDs and both portal
  logins, then **Save**. Writes to `.env`/`credentials/` for you — never
  logs what you typed. Takes effect on the **next app restart** (Settings
  doesn't hot-swap the running session's config). Leaving a password
  field blank on a later edit keeps whatever was already saved — it's
  never blanked out just because you didn't retype it. The Environment
  field itself (MOCK/LIVE) is deliberately read-only here — step 3 below
  stays a separate, manual edit.
- **By hand**: edit `.env` directly, as below.

1. Place the Google service-account JSON in the git-ignored `credentials/`
   folder; reference its path from `.env` (`GOOGLE_SERVICE_ACCOUNT_FILE`,
   `GOOGLE_SPREADSHEET_ID_OGR`/`_UDISE`/`_PEN`).
2. Set `GUJARAT_UDISE_SCHOOL_CODE`/`_USERNAME`/`_PASSWORD` and
   `NATIONAL_UDISE_PLUS_USERNAME`/`_PASSWORD` in `.env` — never hardcoded
   in source (RULEBOOK.md §J6).
3. Set `UDIFY_ENVIRONMENT=LIVE`. `Settings.require_live_credentials()`
   refuses to start in LIVE mode with any of the above missing — it never
   silently falls back to MOCK behavior.

## Run

From source (development):

```
python run_udify.py
```

or the packaged build (see Build below):

```
dist\UdiFy\UdiFy.exe
```

Both launch the same PySide6 GUI (`src/app/main.py`), in MOCK mode by
default — see the Batch Queue screen for a small, clearly-labeled MOCK
sample dataset spanning Conditions 1-4 plus one ND-reconciliation case.

## Test

```
pytest tests/unit
pytest tests/integration       # real Playwright Chromium against fixture-backed mock portals
pytest tests/                  # everything — 51/51 passing as of 2026-09-25
```

There is no separate `tests/live` suite (LIVE-mode testing happens only
at the Live Verification Gate, against real credentials, following the
exact L1-L4 phase sequence and reporting template in TODO.md — not as an
ordinary pytest run). See TODO.md's "Mock scenario checklist" and
"Testing matrix" for what must be covered before a change is considered
verified.

## Build (PyInstaller — TODO.md step 16)

```
pip install pyinstaller   # already in requirements.txt
pyinstaller installer.spec
```

Output: `dist\UdiFy\` — copy the **whole folder** (not just `UdiFy.exe`)
to the target machine; `_internal\` holds required support files
including the bundled Playwright driver and the two MOCK fixture pages.
Chromium itself is **not** bundled (would add several hundred MB for no
benefit before Live Verification runs) — run `playwright install
chromium` once on the target machine too. Verified 2026-09-25 by actually
launching the built `.exe` and confirming the GUI renders and its
SQLite/diagnostics files are created correctly, not just that the build
step exits 0.

**2026-09-26**: on this machine, neither this build nor the one below
launches at all without allowing it through **Smart App Control**
(Windows Security → App & browser control) — a one-way setting (needs a
Windows reinstall to re-enable), so that's the operator's call, not
something to flip automatically. A Start Menu shortcut launching
`.venv\Scripts\pythonw.exe run_udify.py` (already-trusted, signed
binary) works regardless, with no security tradeoff — see
RELEASE-PLAN.md's "Build" section for the full story.

**Single-file build + proper installer (added 2026-09-26)**:
```
pyinstaller installer-onefile.spec        # -> dist\UdiFy.exe (one file)
ISCC.exe installer.iss                    # -> dist_installer\UdiFy-Setup.exe
```
`ISCC.exe` is Inno Setup's compiler (`winget install JRSoftware.InnoSetup`
if not already installed). The resulting `UdiFy-Setup.exe` is a real
Windows installer — Start Menu entry, optional desktop shortcut, proper
uninstaller — installing to `%LOCALAPPDATA%\Programs\UdiFy` (no admin/
UAC needed, and genuinely writable so the app's own SQLite DB lands next
to it correctly). See RELEASE-PLAN.md for the frozen-`PROJECT_ROOT` bug
this depended on fixing first, and the end-to-end verification done.

## Harden

- Confirm `.gitignore` blocks `.env*`, `credentials/`, `*.sqlite3`,
  `diagnostics/`, `build/`, `dist/` (already in place — see repo root
  `.gitignore`).
- Confirm no secret values appear in any `governance/` file before
  staging (RULEBOOK.md §J6/§B) — re-check every session that touches
  `governance/`.
- Confirm Playwright always launches headed/visible for the government
  portals (spec §140/§276) — `run_worker.py` and every screen's
  background worker call `chromium.launch(headless=False)` explicitly;
  never silently switched to headless.

## Where things are

- Master business-rules spec: `governance/planning/UDIFY-SPECIFICATIONS.md`
- Engineering plan / DB design / implementation spec / UI spec / TODO /
  threat model / release plan: `governance/planning/*.md`
- Application code: `src/` (`config`, `db`, `diagnostics`, `sheets`,
  `portals`, `engine`, `app`)
- Tests: `tests/unit`, `tests/integration`, fixture pages under
  `tests/fixtures/`
- Current project state: `governance/BOOTSTRAP.md`
- Session/work logs: `governance/ai-context/`, `governance/work-log/`
