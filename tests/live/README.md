"""Live verification scripts — the reproducible L1-L3 evidence.

**These are not part of `pytest`'s default run.** They touch real Google
Sheets and real government portals, so they must be invoked explicitly and
deliberately:

    .venv\Scripts\python.exe tests\live\L1_authentication.py
    .venv\Scripts\python.exe tests\live\L2_sheets_readonly.py
    .venv\Scripts\python.exe tests\live\L3_national_navigation.py --read-only

Every script here is **read-only unless it says otherwise in its own
docstring**, and each one prints exactly what it observed so the result can
be read rather than inferred. That is the whole purpose: the L1/L2/L3
evidence gathered on 2026-09-26/27 came from throwaway scripts that were
never committed, so it could not be re-run or checked by anyone else. This
directory is where that mistake is not repeated.

Safety rules every script here follows:

- **Never print a credential.** Values are read from `Settings`, and only
  non-secret facts (host, whether a value is set) are ever displayed.
- **Refuse to run in MOCK.** These scripts are meaningless without real
  credentials, and silently testing a mock would produce a false pass.
- **One deliberate session.** Do not add retry loops: repeated logins
  against a government portal can trip fraud detection and get the
  school's real account flagged or locked.
- **A CAPTCHA is a pause, not a failure.** The adapters raise
  `AutomationPausedForUser`; type the code in the visible browser window
  and the script continues.
"""

from __future__ import annotations
