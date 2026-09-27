# BOOTSTRAP.md — UdiFy Current State

> Read this every session (RULEBOOK.md §0/§C.2 — ALWAYS). Curated snapshot,
> not an archive — see RULEBOOK.md §D size-discipline rule.

## Current state (as of 2026-09-27)

- **Phase**: **OPERATE**, **running LIVE**. The full DISCOVERY→RELEASE ladder
  is **complete**.
- **RELEASE gate: APPROVED 2026-09-27**. First scoped to keep
  `UDIFY_ENVIRONMENT` at `MOCK`; **later the same day amended by the user's
  explicit "make everything live"** — LIVE operation against **both real
  portals and all three real registers is now authorised**, without per-run
  sign-off. Recorded as **EX-2026-09-27-01 + EX-2026-09-27-02**
  (RELEASE-PLAN.md), the second being a deliberate, separately-recorded
  widening of the first's risk — not a silent merge.
- **`.env` is `UDIFY_ENVIRONMENT=LIVE`** (set 2026-09-26 for the Live
  Verification Gate). No edit was needed to "go live"; it was already live.
- **⚠️ Read this before running anything.** The app has **never completed a
  single end-to-end live run**. L3 never succeeded, the National New-PEN
  selectors have never touched the real DOM, and the Gujarat portal has never
  been read live at all. Treat every live run as **exploratory**: one
  student, supervised, Diagnostics view open. See "Live Verification Gate"
  below.
- **Gate**: none open. Per RULEBOOK.md §F's already-running-project clause,
  **§J12B PATCH/MINOR/MAJOR classification governs day-to-day work** — the
  release ladder is not re-run per change.
- **Approvals given**: git init; secrets approach; stack lock-in; plan;
  design; UI; **"code it"**; **"test it"**; **"approve release"**.
- **Tests**: **110/110 passing, 0 skipped** (`pytest -q`, 136s) — verified
  2026-09-27, the day of release approval.
- **Git**: local `master` is **26 commits ahead of `origin/master`**
  (unpushed — only push when asked). HEAD `46ecb88`. **13 files of work are
  uncommitted**, see below.

## Real environment versions (this machine — the school's actual
## UDISE-operations machine, confirmed 2026-09-26)

- Python **3.14.7** (`.venv` at repo root) · Git **2.55.0.windows.3**
- Windows 11 Home Single Language, build 26200. Lenovo 83DV.
- Playwright **1.63.0** (Chromium present; every test launches a *visible*
  browser) · PySide6 **6.11.2** (real GUI launched and screenshotted).
- No Node.js dependency.
- **Smart App Control blocks unsigned `.exe` files** on this machine, so the
  PyInstaller build will not launch here. `.venv\Scripts\pythonw.exe
  run_udify.py` (windowless, already trusted) is the real "launch UdiFy"
  path, wired to a Start Menu shortcut. **Never disable Smart App Control** —
  it is the user's decision, and it is a one-way change.

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

## Uncommitted work (not in git — read before assuming HEAD is complete)

13 files, +505/−57: the L3 navigation rebuild. New adapter methods
`open_students_module()` / `choose_current_academic_year()` /
`dismiss_pending_notifications()`, a rebuilt `open_add_student()`, the
identity-field trio, plus the fixture, `branches.py`, `field_mapping.py`,
settings, `.env.example` and 6 test files. **TODO.md (+312 lines) holds the
real engineering record**, including a wrong mid-session "correction" that
was reverted — kept deliberately, because the back-and-forth is the evidence
that selectors were verified rather than guessed.

## Git state

- Remote `origin` = `https://github.com/sectofficework-droid/UdiFy.git`.
- Identity configured by the user: `bkdebiprasaddas-blip
  <bkdebiprasaddas@gmail.com>`.
- `.gitignore` excludes `Scratch/`, `.env*`, `credentials/`, `*.sqlite3`,
  `*.log`, build artifacts. Only `.env.example` (placeholders) was ever
  committed — **no real credential has ever entered git history**, re-verified
  2026-09-26.
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

**RELEASE approved; phase OPERATE, running LIVE.** Nothing is blocking. Since
LIVE is now on, the highest-value next work is no longer optional polish — it
is **verifying the live path that has never actually run**: L2 on the Gujarat
portal (never attempted), then one supervised L3 run on a single test
student. See TODO.md's "Next trigger" for the full menu.

**To change anything of substance now**, say which: a **PATCH** proceeds
directly; a **MINOR CHANGE** gets its spec/TODO updated first; a **MAJOR
CHANGE** reopens the relevant gate. There is no trigger phrase needed to
*stay* in OPERATE — only to reopen a gate.
