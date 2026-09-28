# SETUP-GUIDE.md — UdiFy

> Per RULEBOOK.md §E.6. This covers install/run/configure/test/harden.
> **Status: current as of 2026-09-28**, after mock mode was removed
> entirely (see TODO.md's "Mock mode removed — LIVE-only from now on") —
> the app is now LIVE-only, no MOCK mode exists. Packaging is **deferred**
> (see Build below), not a current step — do not follow packaging
> instructions from before 2026-09-27, they describe a build path that was
> deliberately removed.

## Prerequisites (confirmed on this machine, 2026-09-26)

- **Python**: 3.14.7 (`C:\Python314\python.exe`).
- **Git**: 2.55.0.windows.3.
- **Playwright Chromium**: required for every browser interaction —
  install with `playwright install chromium` after
  `pip install -r requirements.txt` (see Install below).
- **Google Cloud service account + government-portal credentials**: **all
  required**. The app has no non-LIVE mode to fall back to —
  `Settings.require_live_credentials()` refuses to start without every
  one of them. See Configure below.

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

Copy `.env.example` to `.env` and fill in every value — all of them are
required, there is no mode that runs without them. Two ways to fill in
steps 1-2 below — pick whichever is more convenient:

- **Through the app**: launch UdiFy, open **Settings**, browse to the
  service-account `.json` key (copied into `credentials/` automatically)
  and fill in the three spreadsheet IDs and both portal logins, then
  **Save**. Writes to `.env`/`credentials/` for you — never logs what you
  typed. Takes effect on the **next app restart** (Settings doesn't
  hot-swap the running session's config). Leaving a password field blank
  on a later edit keeps whatever was already saved — it's never blanked
  out just because you didn't retype it.
- **By hand**: edit `.env` directly, as below.

1. Place the Google service-account JSON in the git-ignored `credentials/`
   folder; reference its path from `.env` (`GOOGLE_SERVICE_ACCOUNT_FILE`,
   `GOOGLE_SPREADSHEET_ID_OGR`/`_UDISE`/`_PEN`).
2. Set `GUJARAT_UDISE_LOGIN_URL`/`_SCHOOL_CODE`/`_USERNAME`/`_PASSWORD` and
   `NATIONAL_UDISE_PLUS_LOGIN_URL`/`_USERNAME`/`_PASSWORD` in `.env` —
   never hardcoded in source (RULEBOOK.md §J6).

`Settings.require_live_credentials()` refuses to start with any of the
above missing — there is no silent fallback. Other `.env` keys:
`UDIFY_SQLITE_PATH`, `UDIFY_DIAGNOSTICS_DIR`, `UDIFY_LOG_LEVEL` (all
optional, sensible defaults).

## Run

From source — the only working launch path on this machine (Smart App
Control blocks unsigned `.exe` files; see Build below):

```
python run_udify.py
```

or, for the trusted windowless launch the Start Menu shortcut `UdiFy.lnk`
uses:

```
.venv\Scripts\pythonw.exe run_udify.py
```

Launches the PySide6 GUI (`src/app/main.py`) against the real,
LIVE-configured portals and the real Google Sheet — the Batch Queue shows
the school's actual students from the OGR register, loaded fresh on
every launch.

## Test

```
pytest tests/unit
pytest tests/integration
pytest tests/                  # everything — 191/191 passing as of 2026-09-28
```

`tests/live/` is excluded from the default run (scripts, not pytest
tests — they touch the real portals/sheets). Run them individually,
deliberately, per `tests/live/README.md` — never in a retry loop against
the live portals (account-lockout/fraud-detection risk).

## Build — DEFERRED, not a current step

**Packaging was removed 2026-09-27 and deferred to the end of
development** (user decision — see TODO.md's "Packaging: deferred to the
END of development"). There is no `installer.spec`/`installer-onefile.
spec`/`installer.iss` in the tree right now, and none should be
reintroduced before then. `pyinstaller` stays pinned in
`requirements.txt` for when that step actually happens.

**The known blocker for whenever that step is picked back up**: a
PyInstaller build on this machine produces an `.exe` that Windows Smart
App Control refuses to launch (missing code signature, not a packaging-
format issue). Resolving that needs one of: code-signing the build,
a Smart App Control exception (a one-way Windows setting, the user's
decision alone), or accepting source-only operation permanently. See
TODO.md for the full reasoning — do not attempt to "just fix" this by
disabling Smart App Control.

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
- Tests: `tests/unit`, `tests/integration`, live-verification scripts
  under `tests/live/` (see its own README)
- Current project state: `governance/BOOTSTRAP.md`
- Session/work logs: `governance/ai-context/`, `governance/work-log/`
