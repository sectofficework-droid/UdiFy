# DISCOVERY.md — UdiFy

> Per RULEBOOK.md §C0/§E.0. The product idea here is NOT vague — it arrives
> as an exhaustive, video-derived final engineering specification
> (`UDIFY-SPECIFICATIONS.md`, 10,732 lines). This file distills that spec
> into the standard discovery shape so the required deliverable exists and
> is checkable, without re-deriving decisions the user already made. Every
> claim below cites the spec section it comes from; do not treat this file
> as a replacement for the master spec.

## Problem statement

Satyam Stars International School must enter every student into two
government systems — the Gujarat Child Tracking System (state UDISE) and
the National UDISE+ Student Database (PEN) — as a manual, repetitive,
error-prone data-entry task performed by school staff working from an
internal spreadsheet-based register. (Spec §226 "Original business process
before automation".) The work is high-volume, multi-stage (documents arrive
in phases — spec §227), and mistakes are consequential: a wrongly-marked
"complete" record or a duplicated transfer request is a government-data
error, not just a UI bug.

## Target users

- **School administrative staff** (e.g. the observed operator, spec §36)
  who currently perform this entry by hand and will operate the automation
  tool locally on a school Windows machine.
- Indirectly: the students whose records are being entered (data subjects —
  see SECURITY-THREAT-MODEL.md for their protection).

There is no external/public user; this is an internal single-tenant desktop
tool for one school's back-office workflow (spec §AD/§AE: "The desktop
application remains local").

## Core user journeys (REQ-traced in PLAN.md / IMPL-SPEC.md)

1. **REQ-001 — New UDISE + New PEN** (spec Condition 1, §11/§159/§AA/§149):
   operator selects students ready for government entry; the app drives the
   Gujarat UDISE new-entry flow, then the National UDISE+ new-PEN flow, and
   marks both rows GREEN once verified.
2. **REQ-002 — New UDISE + PEN Import** (spec Condition 2).
3. **REQ-003 — UDISE Import + New PEN** (spec Condition 3).
4. **REQ-004 — UDISE Import + PEN Import** (spec Condition 4).
5. **REQ-005 — ND reconciliation**: periodically re-check students whose PEN
   is `ND` against the National UDISE+ database and fill in a real PEN when
   the portal has since assigned one (spec §V/§55-64/§165/§213/§259-263).
6. **REQ-006 — Transfer-request approval monitoring**: batch-check all
   `REQUEST SENT` / LIGHT ORANGE students, separate "Still Pending" from
   "Status Changed", and route status-changed cases to manual review (spec
   §M/§N/§O).
7. **REQ-007 — Manual intervention / diagnostics**: whenever the portal
   presents an unknown state, CAPTCHA, OTP, or Aadhaar consent step, the
   operator is prompted to act manually and the app resumes from checkpoint
   (spec §I/§142/§211).

## Alternatives / competitors

Not discussed in the source material — this is a bespoke internal tool
replacing a fully manual process, not a market product. No competitor
research was requested or performed. (Recorded here as **UNKNOWN** per
§C0.3 rather than invented.)

## Value proposition

Eliminate repetitive, error-prone manual government portal entry while
preserving (not weakening) the school's existing verification discipline —
every business rule in the spec exists specifically to prevent the
automation from being *less* careful than a human operator (no false
GREEN, no fabricated PEN, no duplicate transfer requests — spec §AI items
15-21).

## MVP scope

The spec's own "FINAL COMPLETION STANDARD" (§10485-10508) is the MVP
completion bar. In REQ-ID form, MVP = REQ-001 through REQ-007 above, plus:
- REQ-008 — UI-change resilience (spec Final Authority §B/§C).
- REQ-009 — full audit/event trail (`pen_case_events`, spec §P/§Q/§R/§S).
- REQ-010 — approval history filtering/export (spec §O).

## Non-goals (explicitly out of scope / deferred)

- Any government-portal behavior not evidenced by the nine source
  recordings — implemented as `COMING_SOON` / `MANUAL_REQUIRED` adapters,
  never guessed (spec §AH, §132, §184).
  - "Import" mechanics not shown in these recordings — instead the two
    outcome states (Import Successful / Import Pending) are now confirmed
    at spec §294-302; anything still not shown (e.g. exact button labels)
    remains a live-portal verification task.
- CAPTCHA/OTP automation — always manual (spec §I).
- Cloud hosting / multi-tenant / multi-school — this is a single-school
  local desktop app (spec §AD).
- Mobile/web client — Windows desktop only (spec §AE); §J15B mobile/web
  parity is N/A for this project.

## Success metrics

Not stated as numeric targets in the source material. Recorded as
**UNKNOWN — needs owner input**: e.g. target reduction in manual entry time
per student, acceptable manual-review rate, acceptable ND-reconciliation
backlog. Recommend the user define at least one measurable MVP success
criterion before RELEASE gate (RULEBOOK.md §E.0 requires this); tracked as
an open question below.

## Monetization hypothesis

N/A — internal school tool, not a monetized product.

## Risks

- **Government portal drift**: UDISE/UDISE+ UI can change without notice;
  mitigated by the mandatory UI-change-resilience design (spec Final
  Authority §B/§C) — architecture risk, not a business risk.
  - **Legal/consent risk**: Aadhaar demographic-authentication consent is a
  legally meaningful confirmation (spec §39/§142/§I) — must stay a
  controlled human step unless the school explicitly authorizes otherwise.
- **Data-integrity risk**: incorrect GREEN/PEN/UID writes are hard to
  reverse in a government system — this is why the spec is so strict about
  verification-before-write (spec §D/§J "Consequential action rule" /
  "Spreadsheet integrity rules").
- **Credential/security risk**: government portal logins and Google service
  account keys are sensitive — see SECURITY-THREAT-MODEL.md.
- **Incomplete evidence risk**: some UI sections (Scholarship & Facility,
  Health & CWSN exact field numbering) were "not completely machine
  readable in every frame" (spec §W) — implementation must verify against
  the live DOM, not the spec's field list alone.

## Facts / assumptions / unknowns

**Facts (source-derived, spec-confirmed):**
- Three spreadsheet files, exact headers, four workflow conditions, class
  routing rule, GREEN/ND/LIGHT-ORANGE semantics, required stack — all as
  cited above and in PLAN.md/DB-DESIGN.md.

**Assumptions (engineering design, not video-observed — labeled as such
throughout IMPL-SPEC.md per spec §191/§288):**
- Exact DOM selectors, timing, and some field label text will be confirmed
  against the live portals during implementation, not assumed from
  screenshots.

**Unknowns (explicitly open, per spec §150/§184/§215):**
- Exact click-by-click UDISE Import and PEN Import button sequences beyond
  what §294-302/§W/§X document.
- Numeric MVP success metrics (see "Success metrics" above).
- Google Cloud project / service-account provisioning details (owner to
  provide — see RELEASE-PLAN.md).

## Open questions for the user

1. What does "done" look like in measurable terms (time saved, error rate,
   backlog cleared)? — needed before RELEASE gate.
2. Do you already have a Google Cloud project + service account for Sheets
   API access, or does this need to be created from scratch?
3. Confirm: is CAPTCHA/OTP/Aadhaar-consent always operator-performed with no
   exceptions, as the spec assumes (§I)?

These do not block PLANNING — they are recorded for the "approve plan" /
"approve design" gates.
