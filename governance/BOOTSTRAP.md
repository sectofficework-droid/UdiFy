# BOOTSTRAP.md — UdiFy Current State

> Read this every session (RULEBOOK.md §0/§C.2 — ALWAYS). Curated snapshot,
> not an archive — see RULEBOOK.md §D size-discipline rule.

## Current state (as of 2026-09-27, later)

- **Phase**: **OPERATE**. The DISCOVERY→RELEASE ladder ran, but the
  **RELEASE gate is REOPENED** — see below.
- **🔴 RELEASE REOPENED 2026-09-27.** A full project review found the live
  path **was never wired**: `AppContext` built a real
  `GoogleSheetsRepository` under `UDIFY_ENVIRONMENT=LIVE`, but all three
  GUI screens hardcoded `file:///.../tests/fixtures/*.html` and passed
  `environment="MOCK"` as a literal. `*_LOGIN_URL` settings were parsed and
  never consumed. Clicking "Start run" would have driven mock pages and
  written mock results into the school's **real** spreadsheets. The earlier
  release grant is **withdrawn**, not carried forward. Full record:
  RELEASE-PLAN.md's "REOPENED: the release was unsafe as granted".
- **✅ Remediation implemented and tested (same session, user-authorised as a
  MAJOR change)**: new `src/app/portal_factory.py` is the single place that
  decides real-vs-mock from `Settings`; all three screens use it; no silent
  mock fallback in LIVE; `list_students()` populates the Batch Queue from
  the real OGR register; real students are runnable (the old
  `intended_condition` gate silently disabled them); per-run LIVE
  confirmation dialog. **132/132 tests pass**, including 6 that specifically
  drive the LIVE branch — the branch that previously had zero coverage.
- **`.env` is `UDIFY_ENVIRONMENT=LIVE`.**
- **⚠️ Live wiring is verified; live *execution* is not.** No live run has
  ever been performed. The National Add-Student selectors are still
  video-inferred only, and the Gujarat portal has still never been read
  live. See "Live Verification Gate" below.
- **Gate**: none open. Per RULEBOOK.md §F's already-running-project clause,
  **§J12B PATCH/MINOR/MAJOR classification governs day-to-day work** — the
  release ladder is not re-run per change.
- **Approvals given**: git init; secrets approach; stack lock-in; plan;
  design; UI; **"code it"**; **"test it"**; **"approve release"**.
- **Tests**: **132/132 passing** (`pytest -q`, 107s) — verified 2026-09-27
  after the live-wiring remediation.
- **Git**: local `master` was level with `origin/master` at `455c91c`; the
  live-wiring work is **staged, not committed** (see below).

## Real environment versions (this machine — the school's actual
## UDISE-operations machine, confirmed 2026-09-26)

- Python **3.14.7** (`.venv` at repo root) · Git **2.55.0.windows.3**
- Windows 11 Home Single Language, build 26200. Lenovo 83DV.
- Playwright **1.63.0** (Chromium present; every test launches a *visible*
  browser) · PySide6 **6.11.2** (real GUI launched and screenshotted).
- No Node.js dependency.
- **Smart App Control blocks unsigned `.exe` files** on this machine, so a
  PyInstaller build will not launch here. **`.venv\Scripts\pythonw.exe
  run_udify.py` (windowless, already trusted) is the only working launch
  path**, wired to a Start Menu shortcut `UdiFy.lnk`. Never disable Smart
  App Control — it is the user's decision, and it is a one-way change.
- **Packaging is DEFERRED to the end of development** (user decision,
  2026-09-27: *"we will first final the development then compile to exe"*).
  Nothing to do about it today.
- **⚠️ But the final step has a known blocker, flagged early on purpose.**
  Building an `.exe` on this machine will produce a file that **cannot
  launch** — Windows Smart App Control rejects unsigned executables.
  Verified on both build formats; the block is about the missing code
  signature, not the packaging format. So "compile to exe" needs one of:
  (a) code-sign the build with a certificate the school owns/buys, (b) a
  Smart App Control exception from whoever manages that policy — the
  specific switch is **one-way** on Windows 11 and is the user's decision
  alone, or (c) accept running from source permanently and drop the exe
  idea. Deciding this costs nothing now; finding out at the final build
  would. Full detail: TODO.md's "Packaging: deferred to the END of
  development".
- The `sys.frozen` / `sys._MEIPASS` handling in `settings.py` and
  `mock_fixtures.py` is **deliberately retained** so a future build needs no
  rework.

## Live Verification Gate — where it actually stands

Mock-first through RELEASE. Live progress is **partial**, and the honest
summary is: **read-only and login verified; nothing that writes has ever
completed against a real portal.**

| Phase | State |
| --- | --- |
| L1 Authentication | **PASSED** — Google Sheets (read-only) + both portal logins. 6 real adapter bugs found and fixed live. |
| L2 Sheets half | **DONE** (`e3e7cde`) — `GoogleSheetsRepository` real read/write built; no `NotImplementedError` left in `src/`. |
| L2 Gujarat portal | **NOT ATTEMPTED** — only its login was ever live-checked. |
| L3 controlled student | **NEVER COMPLETED** — attempt #1 failed and exposed the navigation gap below. |
| L4 recovery | Not started. |

**The known live-verification gap**: the National UDISE+ New-PEN flow
(`open_add_student()`, `fill_identity_fields()`,
`read_identity_confirmation()`, `confirm_identity_details()`) was rebuilt
from the project's own screen recordings and has **never run against the real
DOM**. The precise cell-click fix in `open_add_student()` is likewise
unverified. The Gujarat (state) portal has **never been read live at all** —
only its login. This is the substance of EX-2026-09-27-01/02, and it is why
LIVE authorisation does not mean the live path is verified.

> **Account-safety instruction (still in force, narrowed).** The original
> 2026-09-27 instruction — *do not resume live attempts without explicit
> go-ahead* — was **withdrawn for scope** by "make everything live": live
> runs no longer need per-run sign-off. The **underlying concern was not**,
> and still applies: **do not rapid-retry logins.** Repeated real logins
> against the live portal risk tripping fraud detection and getting the
> school's real account flagged or locked. Prefer a single deliberate
> session; if a run fails, diagnose from the Diagnostics view before
> attempting another.

## Folder structure (verified 2026-09-27)

Authoritative, annotated tree with rationale: **PLAN.md's "File map"**.
This file only records the facts most likely to be got wrong:

- **`src/` mirrors the architecture** (`app/`, `engine/`, `sheets/`,
  `portals/{udise_gujarat,udise_plus}/`, `db/`, `diagnostics/`, `config/`)
  and `tests/` splits `unit/` / `integration/` / `fixtures/`. Both were
  already correctly organised and were **not** restructured — the
  untidiness was at ROOT, not inside these.
- **`tests/live/` is EMPTY.** The L1/L2/L3 live-verification evidence came
  from throwaway, uncommitted scripts, so it is not reproducible. The folder
  is reserved so future committed live-verification scripts have a home.
- **No packaging directory** — removed 2026-09-27, see the note above.
- **No `pyproject.toml`** — `requirements.txt` + `pytest.ini` only; a
  pyproject would duplicate dependency truth.
- **`udify.sqlite3` sits at ROOT**, not in a `data/` folder. `data/` was
  briefly added for the (now-removed) installer and reverted.
- Root holds exactly 8 intentional files: `run_udify.py`, `requirements.txt`,
  `pytest.ini`, `.env`, `.env.example`, `.gitignore`, `AGENTS.md`,
  `udify.sqlite3`.
- Ignored-but-present directories (local only, all deliberate): `Scratch/`
  (UI prototype), `UDISE/` (9 recordings, 167 MB), `credentials/`,
  `diagnostics/`, `.venv/`, `.pytest_cache/`, `.claude/`.

## Uncommitted work

**None at the time of writing**, except the folder-structure
reconciliation recorded above (`.gitignore` cache entries + PLAN.md /
BOOTSTRAP.md documentation). The live-wiring remediation and the packaging
removal are committed as `4fd7c97`.

## Git state

- Remote `origin` = `https://github.com/sectofficework-droid/UdiFy.git`.
- Identity configured by the user: `bkdebiprasaddas-blip
  <bkdebiprasaddas@gmail.com>`.
- `.gitignore` excludes `Scratch/`, `.env*`, `credentials/`, `*.sqlite3`,
  `*.log`, `UDISE/` + `*.mp4`, and tool caches (`.pytest_cache/`,
  `.claude/`, `.mypy_cache/`, `.ruff_cache/`). There is deliberately **no**
  packaging section. Only `.env.example` (placeholders) was ever
  committed — **no real credential has ever entered git history**,
  re-verified 2026-09-26.
- **`UDISE/` is now git-ignored** (2026-09-27, explicit user decision: keep
  the source screen recordings out of git). `.gitignore` carries both a
  `UDISE/` rule and a blanket `*.mp4`. Verified: the rule matches, the folder
  no longer appears in `git status`, and **no `.mp4` was ever committed
  anywhere in history** — so nothing needs purging. The recordings remain the
  evidence base the master spec was derived from, but the conclusions are
  recorded in `governance/planning/UDIFY-SPECIFICATIONS.md`, so the videos
  themselves aren't needed to build, test, or audit the project.


## Assumptions on record (user may veto per RULEBOOK.md §C2.3)

- Aadhaar-consent automation stays manual-only, no exceptions — confirmed by
  the user 2026-09-26.
- Data retention: audit trail kept indefinitely, no school policy.
- Encryption at rest: not required, OS-level protection sufficient.
- Release is MOCK-mode only until the user separately enables LIVE.
  **Superseded 2026-09-27**: the user enabled LIVE ("make everything live").
  Retained as a superseded assumption for the audit trail.

## Open questions

1. [x] Numeric MVP success metrics — answered 2026-09-26 (three qualitative
   dimensions, no hard numeric targets).
2. [x] GCP/service account + all 3 real spreadsheets shared — resolved
   2026-09-26.
3. [x] Aadhaar-consent automation — manual only, confirmed.
4. [x] Data retention + encryption at rest — answered 2026-09-26.
5. [x] Disposition of the untracked `UDISE/` recordings — **decided
   2026-09-27**: keep them out of git (git-ignored, local only).
6. [ ] **New**: the 3 unbuilt retry/recovery flows — build them, or continue
   to live under EX-2026-09-27-01.
7. [ ] **New**: LIVE is authorised but unverified end-to-end. The cheapest
   evidence that would retire most of EX-2026-09-27-02 is L2 (Gujarat
   read-only), then one supervised L3 run. Recommend that order.

## Next trigger

**RELEASE gate is REOPENED** (2026-09-27) — the live path was not wired and
the previous grant is withdrawn. The wiring is now built and tested; what
remains is **evidence that a real run works**.

**Recommended order, cheapest first:**
1. **L2 — Gujarat portal, read-only.** Never attempted; only its login has
   ever been live-checked. Retires the largest untested surface.
2. **L3 — one supervised test student.** Verifies the rebuilt Add Student
   navigation and identity-confirm modal against the real DOM. A
   per-run confirmation dialog now guards this in the GUI.

Both need the operator present at the machine. Then say **"approve release"**
again to re-grant, against real evidence rather than an assumption.

**Standing rules**: a CAPTCHA pauses the run for manual completion by
design — never auto-solved. Never rapid-retry logins against the live
portals (fraud-detection / account-lockout risk); one deliberate session,
read the Diagnostics view before retrying. Never disable Smart App Control.

**To change anything of substance now**: a **PATCH** proceeds directly; a
**MINOR CHANGE** gets its spec/TODO updated first; a **MAJOR CHANGE**
reopens the relevant gate. There is no trigger phrase needed to *stay* in
OPERATE — only to reopen or re-grant a gate.
