# SECURITY-THREAT-MODEL.md — UdiFy

> Per RULEBOOK.md §E.7 (required — this application handles minors' PII,
> government identifiers, and third-party portal credentials) and §J15C.

## Assets

- **Student PII**: name, parents' names, DOB, address, mobile numbers,
  Aadhaar numbers, UID/UDISE, PEN — sourced from the school's Google Sheets
  and written into two government systems.
- **Government portal credentials**: Gujarat UDISE (Child Tracking System)
  login and National UDISE+ login for the school's account.
- **Google service-account credentials**: used for Sheets API access.
- **Local SQLite workflow/audit database**: contains student identity
  snapshots, event history, diagnostics (may include screenshots showing
  PII).
- **Diagnostic screenshots/logs**: can incidentally capture on-screen PII
  from government portal pages.

## Trust boundaries

1. Local operator (school staff) ↔ desktop application (trusted, but
   consequential actions still require verification per IMPL-SPEC.md).
2. Desktop application ↔ Google Sheets API (authenticated via service
   account; scope should be limited to the three operational workbooks).
3. Desktop application ↔ Gujarat UDISE / National UDISE+ portals
   (authenticated via school's own portal credentials; these are
   third-party government systems outside this project's control).
4. Desktop application ↔ local filesystem (SQLite DB, logs, screenshots,
   credentials file) — single-machine, no network exposure by design (spec
   §AD: "the desktop application remains local").

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Credential leakage (portal login, Google service-account key) in code, logs, or git history | Never hardcoded; local `.env` + git-ignored `credentials/` folder (user-confirmed 2026-09-25); `.gitignore` covers `.env*`, `credentials/`, service-account/token files; RULEBOOK.md §J6 redaction rules apply to every log line, not just obvious secret fields (spec §141/§178, §L8). |
| Aadhaar demographic-authentication consent performed without real authorization | Treated as a controlled human-intervention point by default (spec §39/§142/§I); automating the click requires an explicit, separately recorded user authorization — not a default. |
| PEN Import's Aadhaar-availability check (added 2026-09-25) submits a student's Aadhaar number to the National UDISE+ portal and, on a match, receives back *another school's* student record (name, DOB, class) and staff contact details (Head of School name and phone number via "HOS Details") | This is inherent to the government workflow itself (spec "PEN IMPORT — OTHER SCHOOL ACTIVE" §6-8/§14), not a design choice this app can avoid — but the app must still minimize exposure of that cross-school data: never write another school's HOS contact info anywhere except the `IMPORT PENDING` sheet fields the spec actually requires (spec §16), never log it beyond that, and never surface it in diagnostics/screenshots more broadly than necessary to resolve a manual-review case. |
| CAPTCHA/OTP bypass or automation | Explicitly prohibited (spec §I) — always manual. |
| False "success" written to a government spreadsheet (wrong UID/PEN, false GREEN, fabricated PEN) | Consequential-action verification rule is mandatory for every write (IMPL-SPEC.md, spec §D/§J); `pen_case_events` provides a tamper-evident, append-only audit trail (DB-DESIGN.md §B.1). |
| Duplicate transfer-request / duplicate PEN initialization from a lost confirmation | Retry-safety rule: non-idempotent actions require state verification before retry, never blind repetition (spec §G, §AI.19). |
| Wrong student acted upon (IDOR-equivalent for this domain — operating on the wrong row) | Multi-attribute student identity verification before every consequential action (spec §E of Final Authority); ambiguous match → manual review, never auto-pick. |
| PII exposure via diagnostic screenshots/logs | Redact known-sensitive fields where feasible; restrict diagnostics storage to the local, git-ignored area; access limited to the operating school staff (RULEBOOK.md §J0N-adjacent concern — applies by analogy since this isn't a file-upload feature, but the "never treat client input as trusted/never over-expose" spirit applies to portal-scraped text too). |
| Unauthorized access to the local SQLite DB / credentials on a shared machine | Out of this application's control surface beyond standard OS file permissions; document as an operational assumption in RELEASE-PLAN.md rather than building bespoke access control not requested. |
| Google Sheets API over-scoping | Service account should be granted access only to the three operational spreadsheets, not broader Drive/Sheets scope, per least-privilege (RULEBOOK.md §J0B.1). |
| Supply-chain risk in Python dependencies (Playwright, PySide6, google-api libraries, openpyxl) | Standard dependency discipline applies at CODING time — pin versions, review before adding (RULEBOOK.md §J7/§J0I); no dependency has been added yet, so no current risk to record. |
| A mock-test result mistaken for a real government/spreadsheet success, given the mock-first development decision (2026-09-25) | Every `pen_case_events`/workflow-run row carries a mandatory `environment = MOCK \| LIVE` field (DB-DESIGN.md §B.1/§B.4); `MOCK_SUCCESS` and `LIVE_VERIFIED_SUCCESS` are distinct case-status values that must never be conflated; a mock run must be structurally incapable of writing to a real spreadsheet or claiming government completion (master spec "CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION" §5). |

## Authorization model

Single-operator, single-tenant desktop tool — no multi-user roles are
specified in the source material. If the school later needs multiple
operators with different permissions (e.g. who may authorize Aadhaar
consent automation, or who may resolve a Status-Changed case), that is a
MAJOR CHANGE (RULEBOOK.md §J12B) requiring explicit scope re-approval, not
something to build speculatively now.

## Data handling

- **Collection**: student PII already exists in the school's own Google
  Sheets; this application reads it, does not originate new collection.
- **Retention**: SQLite audit trail is intentionally durable/append-only
  (spec §P) for accountability — retention/deletion policy for this local
  DB is not specified by the source material; flag as an **open question**
  for the school (e.g. does the school have an internal data-retention
  policy this must follow?).
- **Third-party processors**: Google (Sheets API) and the two government
  portals are the only external parties data reaches; no other analytics/
  storage/messaging vendor is in scope.
- **Encryption**: local SQLite DB and credentials file are not specified as
  encrypted-at-rest by the source material; relying on OS-level disk/user
  protections is the current assumption — record as an open item if the
  school requires stronger at-rest protection.

## Verification before RELEASE gate

Per RULEBOOK.md §J16/§E.7, before "approve release":
- Confirm no secrets are present anywhere in tracked git history
  (`git check-ignore -v` on the real credentials file, per RULEBOOK.md
  §J6).
- Confirm the Aadhaar-consent automation question (DISCOVERY.md open
  question 3) has an explicit answer from the school.
- Confirm the data-retention open question above has an answer or an
  explicit "not required" decision from the school.
