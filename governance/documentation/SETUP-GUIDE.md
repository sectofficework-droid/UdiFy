# SETUP-GUIDE.md — UdiFy

> Per RULEBOOK.md §E.6. This covers install/run/configure/test/harden.
> **Status: skeleton — no application code exists yet (PLANNING gate).**
> Commands below are the intended setup once CODING starts; none have been
> executed/verified yet, so nothing here is claimed as tested
> (RULEBOOK.md §J13).

## Prerequisites (confirmed on this machine, 2026-09-25)

- **Python**: 3.14.7 (`C:\Python314\python.exe`) — confirmed installed.
- **Git**: 2.55.0.windows.3 — confirmed installed; repo initialized this
  session.
- **Playwright browsers**: not yet installed — `playwright install` is a
  CODING-time step once Playwright is added to `requirements.txt`.
- **Google Cloud service account / government-portal credentials**: not
  needed to install, build, or run the app in mock mode — decision
  2026-09-25 was explicitly **mock-first** (master spec "CREDENTIALS,
  MOCKING AND LIVE VERIFICATION DECISION"). Real credentials are
  configured later, only for the Live Verification Gate (TODO.md).

## Install (planned — not yet created)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

`requirements.txt` does not exist yet — it is created at CODING setup
(PLAN.md file map) pinning: PySide6, playwright, google-api-python-client
(or equivalent Sheets client), openpyxl, pyinstaller, plus their exact
versions per RULEBOOK.md §A.8 (real versions, not guessed).

## Configure (planned)

**Mock mode (default — no real credentials needed):** `.env.example` →
`.env` ships with mock mode as the default; the app runs fully against
`MockSheetsRepository` and mocked portal pages with no further
configuration.

**Live mode (only at the Live Verification Gate, TODO.md):**
1. Place the Google service-account JSON in the git-ignored `credentials/`
   folder; reference its path from `.env` (`GOOGLE_SERVICE_ACCOUNT_FILE`,
   `GOOGLE_SPREADSHEET_ID`).
2. Configure government portal login handling per the mechanism decided
   at CODING time (never hardcoded — RULEBOOK.md §J6).
3. Set the environment switch to `LIVE` (exact config key TBD at CODING).

## Run (planned)

```
python -m src.app
```

(Exact entry point to be confirmed once `src/app/` exists. Runs in mock
mode by default.)

## Test (planned)

```
pytest tests/unit
pytest tests/integration          # runs against MockSheetsRepository + mocked portal pages
pytest tests/live -m live         # Live Verification Gate only, real credentials required
```

See IMPL-SPEC.md "Acceptance tests", TODO.md "Testing matrix" and TODO.md
"Mock scenario checklist" / "Live Verification Gate" for what must be
covered before a change is considered verified. Do not run `tests/live`
without completing the mock scenario checklist first.

## Harden (planned)

- Confirm `.gitignore` blocks `.env*`, `credentials/`, `*.sqlite3` (already
  in place — see repo root `.gitignore`, verified via
  `git check-ignore -v` at scaffold time).
- Confirm no secret values appear in any `governance/` file before staging
  (RULEBOOK.md §J6/§B — done for this initial scaffold; re-check every
  session that touches `governance/`).
- Confirm Playwright always launches headed/visible for the government
  portals (spec §140/§276) — never silently switched to headless.

## Where things are

- Master business-rules spec: `governance/planning/UDIFY-SPECIFICATIONS.md`
- Engineering plan / DB design / implementation spec / UI spec / TODO /
  threat model / release plan: `governance/planning/*.md`
- Current project state: `governance/BOOTSTRAP.md`
- Session/work logs: `governance/ai-context/`, `governance/work-log/`
