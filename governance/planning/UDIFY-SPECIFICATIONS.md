# SATYAM GOVERNMENT STUDENT ENTRY AUTOMATION — FINAL ENGINEERING SPECIFICATION

**Status: FINAL / AUTHORITATIVE ENGINEERING SPECIFICATION**
**Purpose: Complete implementation specification for an autonomous coding agent**

> This document is the authoritative project specification. Earlier drafts, archived handoffs, and obsolete statements inside earlier versions must not be treated as current requirements. Where an earlier section conflicts with the final authority sections, the final authority section wins.

## FINAL SOURCE-OF-TRUTH RULE

This specification is built from: (1) the project conversation and explicit user decisions, (2) the project source recordings available in the working project, (3) the supplied UDISE/PEN workbooks, and (4) implementation requirements explicitly established during the project. Video-observed behavior, user-declared business rules, and engineering design decisions are deliberately distinguished. Do not invent undocumented government-portal behavior.

## COMPLETENESS AND AUDIT RULE

The implementation agent MUST begin by reading this entire document and must not treat it as a short summary. The specification intentionally preserves detailed observations, workflow rules, spreadsheet semantics, state transitions, recovery requirements, database requirements, UI requirements, and future-work boundaries. Before coding, the agent must create its own implementation checklist from this document and map each requirement to code/tests.

The nine source recordings currently present in the project are explicitly incorporated into this specification: `GOOGLE SHEET.mp4`, `GUJARAT ENTRY.mp4`, `AFTER UDISE ENTRY BEFORE PEN .mp4`, `PEN ENTRY.mp4`, `5 ND MANUAL UPDATE.mp4`, `UDISE IMPORT (OTHER SCHOOL ACTIVE).mp4`, `PEN IMPORT (OTHER SCHOOL ACTIVE).mp4`, `PEN REQUEST SENT .mp4`, and `HOW TO VIEW SENT REQUEST.mp4`. Their measured durations and source roles are recorded later in this document.

**Important:** “100% complete” means the specification contains all requirements and source observations currently available to the project; it must not claim that an unobservable future government-portal behavior has been verified. Future recordings or live-portal evidence may extend this specification. When that happens, the new evidence becomes authoritative for the previously undocumented workflow without rewriting already-established business rules.

---

# SATYAM SCHOOL — GOVERNMENT STUDENT ENTRY AUTOMATION
## MASTER EXPERT HANDOFF / VIDEO-DERIVED WORKFLOW SPECIFICATION
### Version: 2.0 — Detailed reconstruction of all workflows analyzed so far

> **Purpose:** This file is the authoritative continuity document for the next ChatGPT/account/coding-agent session.
>
> The user wants to continue the project **without re-uploading the already analyzed videos**. This Markdown file is a **complete project context/handoff file for the next ChatGPT or coding session**. This document therefore records not only the high-level process, but also the observed screens, field names/roles, sheet columns, status meanings, button behavior, portal navigation, example values, completion signals, and automation implications.
>
> **Do not replace source-derived details with generic assumptions.**
>
> **Do not invent missing import workflows.**
>
> The four workflow conditions are defined. Dedicated UDISE ACTIVE import and PEN OTHER SCHOOL ACTIVE import recordings are available and are authoritative for their observed import/request workflow. Do not revert these branches to the old "pending because video not supplied" state. Any behavior not explicitly established by the recordings remains Coming Soon / unresolved.

---

# 1. PROJECT GOAL

The school wants a Windows desktop automation application for repetitive student government-data entry.

The eventual system should:

1. Read the relevant student records from Google Sheets.
2. Determine the student's applicable workflow condition.
3. Determine class-based portal/ID routing.
4. Open/control the required government portal in a real browser.
5. Perform the correct UDISE and/or PEN workflow.
6. Handle structured forms, dropdowns, dependent fields, validations, and completion dialogs.
7. Verify actual portal completion.
8. Update the correct Google Sheet record/status.
9. Preserve the distinction between NEW, IMPORT, ND, actual PEN, and completed/green rows.
10. Log each student result.
11. Support retry/resume/manual intervention when the portal behaves unexpectedly.
12. Later support a separate **ND PEN checking** operation.

The user wants workflow discovery to be completed **before writing the final coding-agent prompt or application code**.

---

# 2. SOURCE MATERIAL ALREADY ANALYZED

The following recordings were analyzed during the project:

| Source | Duration | What it established |
|---|---:|---|
| `GOOGLE SHEET.mp4` | ~1:55 | The three working sheets/files, OGR entry order, student record staging |
| `GUJARAT ENTRY.mp4` | ~10:44 | Gujarat UDISE new-student entry and detailed UDISE form workflow |
| `AFTER UDISE ENTRY BEFORE PEN .mp4` | ~2:03 | Post-UDISE sheet state, UID update, relationship between OGR/UDISE/PEN states |
| `PEN ENTRY.mp4` | ~6:15 | National UDISE+ new PEN profile workflow, initialization, profiles, completion, PEN sheet update |
| `5 ND MANUAL UPDATE.mp4` | ~1:52 | Later ND→actual-PEN checking workflow |

The source recordings available for this project include the original five workflow recordings plus later recordings for UDISE ACTIVE import, PEN OTHER SCHOOL ACTIVE import, PEN REQUEST SENT, and HOW TO VIEW SENT REQUEST. The final specification must preserve all source-derived observations and later conversation corrections. The current runtime contains the original video files; this specification must not claim an undocumented workflow merely because a previous handoff said it was pending.

---

# 3. THREE WORKING FILES — EXACTLY THREE

The workflow uses three operational spreadsheet files:

1. **ONLINE GENERAL REGISTER**
2. **UDISE_Entry_(State)**
3. **PEN_Entry_(National)**

Do not create a fictional fourth "master" spreadsheet.

---

# 4. ONLINE GENERAL REGISTER (OGR)

## 4.1 Role

OGR is the school's general register.

It is where **every student record is recorded**.

It is **not** a separate master database that replaces the other two operational sheets.

A student may be recorded in OGR in stages.

---

## 4.2 OGR Initial Entry Order

The Google Sheet recording clearly demonstrated the initial/basic entry pattern:

1. `AY`
2. `NAME`
3. `STD`
4. `MOBILE 1`
5. `MOBILE 2`
6. `PR`

The later information includes:

7. `DOB`
8. `DOA`
9. `DOE`
10. `AADHAR`
11. `UID`
12. `PEN`

Visible OGR columns in the later recording include:

- AY
- NAME
- STD
- MOBILE 1
- MOBILE 2
- PR
- T-GR
- TC
- DOB
- DOA
- DOE
- AADHAR
- UID
- PEN
- APAAR
- DOCUMENTS PENDING

The exact full OGR column set can vary by horizontal scroll/view, but the above fields were visibly used in the workflow.

---

## 4.3 OGR Example from Video

Aisha's OGR row was visible with:

- AY: `2026-27`
- NAME: `AISHA BISOYI`
- STD: `SR KG`
- MOBILE 1: `9337302202`
- PR: `P091`
- DOB: `02/01/2022`
- DOA: `18/05/2026`
- DOE: `23/09/2026`
- AADHAR: `617750014825`
- UID: `242241000672620025` (visible in the analyzed sheet)
- PEN: initially blank/ND depending on stage

The example is for understanding the workflow; the values are not to be hardcoded into software.

---

## 4.4 OGR Color Rule

The user explicitly established:

**OGR row color does NOT become GREEN as part of the government-entry completion workflow.**

Do not introduce an OGR-green completion rule.

The government-entry completion colors belong to the UDISE/PEN operational records.

---

# 5. UDISE_Entry_(State)

## 5.1 Tabs

The analyzed workbook has:

- `PH1`
- `PH2`
- `PH3`

The workbook inspected during analysis contains these exact tabs.

---

## 5.2 Exact UDISE Spreadsheet Headers

The workbook structure inspected during analysis showed these headers:

1. `REMARK`
2. `Class`
3. `UDISE No`
4. `Birth Cert Reg No`
5. `Birth Year`
6. `Birth Month`
7. `Birth Date`
8. `Gender`
9. `Birth State`
10. `Birth District`
11. `Birth City`
12. `Student Name`
13. `Father's Name`
14. `Mother's Name`
15. `Surname`
16. `Date of Birth`
17. `GR No`
18. `Roll No`
19. `Plot Number`
20. `Society`
21. `Landmark`
22. `Area`
23. `Pin Code`
24. `Mother Tongue`
25. `Date of Join`
26. `Aadhar Card No`
27. `Name as per Aadhar`
28. `Mobile No 1`
29. `Mobile No 2`

There is an additional blank/unused column in at least one PH3 export.

---

# 6. UDISE PHASE / GREEN RULE

The UDISE records are grouped into PH1/PH2/PH3.

These phases represent operational batches/document readiness, not different student data models.

## Critical completion rule

When a UDISE student has been successfully completed:

> **CHANGE THE ENTIRE UDISE ROW TO GREEN.**

Do not mark only the UDISE number/UID cell green.

A green UDISE row means the UDISE work for that record has been completed.

---

# 7. PEN_Entry_(National)

## 7.1 Tabs

The analyzed workbook has:

- `PH1`
- `PH2`
- `PH3`
- `IMPORT PENDING`

---

## 7.2 Exact PEN Main Headers

The workbook inspected during analysis showed:

1. `PEN`
2. `Class`
3. `Student Father Surname`
4. `Gender`
5. `Date of Birth`
6. `Student State Code (UDISE No)`
7. `Mother's Name`
8. `Father's Name`
9. `Aadhar Number of Student`
10. `Name of Student as per Aadhar Card`
11. `Admission Date`
12. `Full Address`
13. `Pincode`
14. `Mobile No 1`
15. `Mobile No 2`
16. `Mother Tongue`
17. `Admission Number in Present School (GR No)`
18. `Roll No`
19. `Previous Class Percentage`
20. `Previous Class Attendance Days`
21. `Height (cm)`
22. `Weight (kg)`

The PH3 export contains extra blank columns in the inspected workbook.

---

# 8. PEN IMPORT PENDING TAB

The `IMPORT PENDING` tab has a different structure.

Observed headers:

1. `SR NO`
2. `STUDENT NAME`
3. `PEN`
4. `DOB`
5. `SCHOOL NAME`
6. `SCHOOL UDISE`
7. `STATE`
8. `DISTRICT`
9. `BLOCK`
10. `HEADMASTER`
11. `CONTACT NO`
12. `STATUS`
13. `REMARK`

Example records in the analyzed workbook included:

- `SOUMYA RANJAN BEHERA`
- PEN `23060444551`
- school/state/source-school information
- status `ACTIVE`
- remark `IMPORT PENDING`

Another example:

- `REYANSH SURJYAMANI PATRA`
- PEN `23428960733`
- state `GUJARAT`
- district `SURAT`
- block `SURAT CORPO.`

This strongly indicates that imported PEN records are tracked differently from ordinary new PEN rows.

The dedicated PEN OTHER SCHOOL ACTIVE import recording is authoritative for the observed import-request flow. Any exact step not visible in that recording remains explicitly undocumented rather than invented.

---

# 9. CORE IDENTIFIER DEFINITIONS

## 9.1 UID / UDISE

For this project:

**UID = UDISE**

The Gujarat UDISE workflow produces an **18-digit UDISE/UID**.

---

## 9.2 PEN

PEN is the Permanent Education Number.

When generated, it is an **11-digit number** in the user's workflow.

---

## 9.3 NA vs ND — VERY IMPORTANT

This distinction was explicitly clarified by the user.

After a new student profile is created on the national UDISE+ portal, the portal can show:

**NA = Not Available**

The user's spreadsheet representation is:

**ND = Not Defined**

Therefore:

```text
UDISE+ portal: NA / Not Available
            ↓
School PEN sheet: ND / Not Defined
```

Do not confuse these two labels.

---

# 10. GOVERNMENT PROCESS ORDER

The user's established sequence is:

```text
UDISE FIRST
    ↓
PEN SECOND
```

This ordering applies to the normal New/New condition.

Imported branches may skip a new-entry operation because the record already exists/imports, but the overall student data process remains based on UDISE and PEN status.

---

# 11. FOUR ENTRY CONDITIONS

These are the four official branches defined by the user.

## CONDITION 1
### NEW UDISE ENTRY + NEW PEN ENTRY

- UDISE = New
- PEN = New

**Already fully recorded.**

---

## CONDITION 2
### NEW UDISE ENTRY + PEN IMPORT

- UDISE = New
- PEN = Import
- PEN/student already exists from another school.
- User specifically described the case as **Other State**.
- User said this branch contains **major changes**.

The New UDISE flow remains the same.

Only the PEN Import portion differs.

PEN Other School ACTIVE import behavior is documented from the dedicated recording; do not substitute the old pending statement.

---

## CONDITION 3
### UDISE IMPORT + NEW PEN ENTRY

- UDISE = already available/imported
- PEN = New

The New PEN workflow is already recorded.

The UDISE Import workflow is still pending.

---

## CONDITION 4
### UDISE IMPORT + PEN IMPORT

- UDISE = Import
- PEN = Import

Both import-specific processes remain pending.

---

# 12. CLASS-BASED ID ROUTING

Established rule:

| Student Class | Portal/ID route |
|---|---|
| JrKG | Satyam School ID |
| SrKG | Satyam School ID |
| Balvatika | Satyam School ID |
| 1st | Satyam School ID |
| 2nd and above | Block ID |

This rule applies to both UDISE and PEN workflows.

The exact login/credential mechanism must remain configurable and secure.

---

# 13. GUJARAT UDISE PORTAL — OBSERVED NEW ENTRY FLOW

Source:

`GUJARAT ENTRY.mp4`

Approximate duration:

~10 minutes 44 seconds.

Portal visible in video:

Gujarat Child Tracking System / Gujarat UDISE.

The browser URL visibly used the Gujarat school/student-management system.

School shown:

**SATYAM STARS INTERNATIONAL SCHOOL**

---

# 14. GUJARAT UDISE LEFT NAVIGATION

The recording visibly showed a left navigation including student functions such as:

- Home
- Manage Students
- Student Tracking Report
- Student Transfer Request List
- GSRSE Voucher
- Back To School Phase2
- Attendance Report
- Student Identity (SID) Number Entry
- Early Warning System
- Add Local Holiday

and teacher/school/program sections.

For automation, the important area is the student workflow.

---

# 15. UDISE — STUDENT NEW ENTRY SCREEN

The video shows:

**STUDENT NEW ENTRY**

There are two visually distinct birth-information routes:

1. CRS-RGI verified/retrieval route
2. Manual entry route

Do not hardcode the assumption that every student uses CRS-RGI.

---

# 16. UDISE — CRS-RGI ROUTE

Observed fields:

- birth certificate-related selector
- `Birth Registration No. (BRN)`
- Birth Year
- Birth Month
- Birth Date
- Gender

Button:

**GET DETAILS FROM CRS-RGI**

The demonstrated example used:

- BRN around `13/2022`
- Year `2022`
- Month `01 - January`
- Date `02`
- Gender selected separately

The exact BRN is student-specific.

---

# 17. UDISE — GENDER DROPDOWN

The recording showed a gender dropdown with options including:

- Male
- Female
- Other

The portal displays these with Gujarati/English mixed labeling.

Automation should select by semantic option value/text rather than screen coordinates.

---

# 18. UDISE — MANUAL BIRTH ENTRY ROUTE

When manual entry is used, the screen exposes fields for:

### Birth location
- Birth State
- Birth District
- Birth Taluka
- Birth City/Place
- Birth Village

The recording showed an example:

- Birth State: `Odisha`
- Birth District: `GANJAM`
- Birth Taluka: `SHERAGADA`
- Birth City/Place: selected/related to SHERAGADA
- Birth Village: `SHERAGADA`

### Birth date
- Birth Year
- Birth Month
- Birth Date

### Birth registration
- Whether BRN exists / BRN-related yes/no
- Birth Certificate No. (BRN No.)
- Birth Certificate PDF upload

There is a visible:

**Next**

button.

The upload area shows a file chooser and red instructional text about PDF size/format. Exact maximum size should be read from the live portal rather than hardcoded from the screenshot.

---

# 19. UDISE — MANUAL ENTRY EXAMPLE

The video filled a sample:

- State: Odisha
- District: Ganjam
- Taluka: Sheragada
- Birth location: Sheragada
- Year: 2022
- Month: January
- Date: 02
- BRN: `13/2022`
- BRN present: Yes
- PDF attached

This was the birth-data example for Aisha.

---

# 20. UDISE — NEW STUDENT CTS DETAILS

Below the birth section, the recording showed a section for new student CTS information.

Visible fields were:

1. Student/child name
2. Father's name
3. Mother's name
4. Surname
5. Date of birth
6. Whether child is disabled
7. Type of disability

Button:

**ADD NEW STUDENT**

The example was filled approximately as:

- Student: `AISHA`
- Father: `TOFAN`
- Mother: `PRIYANKA`
- Surname: `BISOYI`
- DOB: `02/01/2022`
- Disabled: `No`
- Disability type: not applicable/blank because disabled = No

Important:

The portal may conditionally enable disability-type fields when the disability answer changes.

---

# 21. UDISE — AFTER ADD NEW STUDENT

The student is then available in the student-management system.

The recording showed a student list with columns such as:

- Aadhaar/UID
- Student Name
- Father Name
- Mother Name
- Surname
- DOB
- DOA
- GR No
- Section
- Status
- Edit

The list also showed an edit/pencil action.

---

# 22. UDISE — MANAGE STUDENTS PROFILE

The detailed student-management screen has five major tabs:

1. **Personal**
2. **Education**
3. **Bank**
4. **Scholarship & Facility**
5. **Health & CWSN**

This is critical:

> UDISE completion is not just generating an 18-digit UID.

The relevant student profile must be completed through the required sections.

---

# 23. UDISE PERSONAL TAB — OBSERVED FIELD GROUP

The video showed a numbered personal form.

Observed fields/values included:

1. Child/student name
2. Father's name
3. Mother's name
4. Surname
5. Guardian's name
6. Social category / category-type field
7. Religion
8. Location/city/district-related selection
9. Area/locality
10. PIN code
11. Address/landmark-related field
12. House/address line
13. Village/area
14. PIN
15. Mother tongue
16. Date of birth
17. Gender
18. Social/economic category fields
19. Religion/category-related selection
20. Additional category/status field
21. Aadhaar-related field
22. Name as per Aadhaar
23. Class/grade
24. Additional status/category field
25. Contact/address-related field
26. Email/contact-related field
27. Email ID / other contact field

The exact Gujarati labels for some numbered fields are not reliably readable in every frame, so the implementation must inspect the live DOM labels rather than infer a field from its number alone.

---

# 24. UDISE PERSONAL — OBSERVED Aisha VALUES

Visible values included:

- Student: `AISHA`
- Father: `TOFAN`
- Mother: `PRIYANKA`
- Surname: `BISOYI`
- Guardian: `TOFAN BISOYI`
- Area/locality: `PANDESARA`
- City/district selection: `2422-SURAT`
- Corporation/local body selection: `SURAT CORPO.`
- Landmark/address: `SHREE RAMNAGAR`
- Road: `BAMROLI ROAD`
- PIN: `394221`
- Mother Tongue: `12-Odia`
- DOB: `02/01/2022`
- Gender: `2-Girl`
- Category: `1-General`
- Religion: `11-General` / portal-coded value
- Language/medium-related values
- Class: `1st` in the visible sample field context where applicable

Some displayed values are portal codes and should not be replaced with generic English labels without mapping the live option values.

---

# 25. UDISE PERSONAL — SAVE

At the bottom of the Personal form:

**SAVE STUDENT**

and:

**CLEAR**

buttons are visible.

The automation should not assume a section is saved merely because fields were filled.

---

# 26. UDISE EDUCATION TAB

The second tab is:

**Education**

The video showed numbered fields approximately in the 28–41 range.

Observed categories included:

- Admission number
- Previous/current class information
- Academic date
- Class/grade
- RTE-related status
- previous academic status
- previous-class result/percentage
- attendance
- medium/language
- school/education-related fields
- subject/language fields
- school medium/English-related value

The exact labels are partly Gujarati in the source video.

---

# 27. UDISE EDUCATION — IMPORTANT OBSERVED VALUES

The recording showed examples such as:

- PR/admission code: `P091`
- Roll/admission-related number: `91`
- Admission date: `18/05/2026`
- Class code: `102-Sr.KG`
- Medium/language: `English`
- Previous-class/status choices
- Other educational status dropdowns

A dropdown was opened and showed a list of class values such as:

- PP-3
- PP-2
- PP-1
- I
- II
- III
- IV
- V
- VI
- VII
- VIII
- IX
- X
- XI
- XII

This demonstrates that the Education form contains class-dependent selection controls.

---

# 28. UDISE EDUCATION — LANGUAGE/SUBJECTS

The national/UDISE education form included:

- medium of instruction
- languages studied
- selected language group
- foreign language, where applicable
- mandatory/general subjects
- additional subjects
- co-curricular subjects

The portal may enable/disable fields depending on class/education level.

Therefore automation must use conditional logic.

---

# 29. UDISE BANK TAB

The third tab:

**Bank**

The recorded screen showed numbered bank-related fields around 42–46.

In the example, several values were:

`NA`

or blank/non-applicable.

The important automation rule is:

> Do not force fake bank values simply because the form has bank fields.

If the correct school/student record legitimately has `NA`, preserve/use the appropriate portal value.

---

# 30. UDISE SCHOLARSHIP & FACILITY TAB

The fourth tab:

**Scholarship & Facility**

The source recording confirms this is a separate profile section.

It must be included in the workflow when required by the portal.

Exact field-by-field values were not all captured at a sufficiently readable level in the available frames.

Therefore:

- the section exists,
- it is part of the completion process,
- exact field mapping remains a live-portal verification task.

Do not invent values.

---

# 31. UDISE HEALTH & CWSN TAB

The fifth tab:

**Health & CWSN**

The visible lower portion contained fields around 62–81.

Observed subjects include:

- CWSN status
- disability-related fields
- impairment type
- UID/UDID-related information
- specific learning disability
- dysgraphia
- dyscalculia
- dyslexia
- autism spectrum disorder (ASD)
- attention deficit hyperactivity disorder (ADHD)
- intellectual/development-related disability
- folic/iron-related facility
- vitamin-A-related facility

The exact numbering/label text should be mapped from the live portal.

For a non-CWSN student, the portal can show `NA` or non-applicable states.

---

# 32. UDISE FINAL SAVE / COMPLETION

The workflow eventually uses:

**SAVE STUDENT**

The user explicitly clarified:

After UDISE is successfully completed:

1. all relevant pending UDISE information is completed,
2. UDISE success is verified,
3. the **entire UDISE row is changed GREEN**,
4. OGR row color remains unchanged,
5. then the PEN workflow can proceed.

---

# 33. AFTER-UDISE RECORD STATE — CRYSTAL-CLEAR HANDOFF BETWEEN UDISE AND PEN

## 33.1 Purpose of this state

This section defines the exact **business state after UDISE entry has been completed and before the PEN workflow is executed**.

This is NOT merely a note saying “UID is populated.” It is a formal handoff state in the automation state machine. A future developer must be able to determine:

1. what has already been completed,
2. what has not yet been completed,
3. which spreadsheet cells should change,
4. which spreadsheet cells must NOT change,
5. whether the student is ready for PEN processing,
6. which PEN branch should be selected, and
7. what must happen if the expected state is not present.

Source recording:

**AFTER UDISE ENTRY BEFORE PEN .mp4**

Approximate recording duration: **2 minutes 03 seconds**.

The recording is a post-UDISE handoff/state recording. It demonstrates the resulting record state before PEN processing. It should not be interpreted as a second full UDISE-entry tutorial.

---

## 33.2 What the automation must understand

For a normal New UDISE → New PEN student, the expected sequence is:

```text
OGR student data prepared
        ↓
UDISE branch executed
        ↓
UDISE profile completed
        ↓
UDISE success verified
        ↓
UDISE sheet row → GREEN
        ↓
OGR UID → populated
        ↓
OGR PEN → still pending / ND / applicable pending state
        ↓
PEN branch becomes eligible
        ↓
PEN workflow starts
```

The critical point is:

> **UDISE completion and PEN completion are two separate states.**

A student having a valid UID/UDISE does NOT mean that the PEN workflow has been completed.

---

## 33.3 Chronological state reconstruction from the recording

### STEP 1 — UDISE work has already been performed

At the beginning of this recording, the student has already passed through the UDISE entry process documented in `GUJARAT ENTRY.mp4`.

Therefore, this recording must be treated as the **post-UDISE checkpoint**, not as the beginning of a new UDISE entry.

The automation should therefore NOT:

- create the student again in UDISE,
- enter the birth details again,
- reopen every UDISE profile section unnecessarily,
- assume that a blank PEN means UDISE failed.

Instead, it should inspect the stored record and continue from the next incomplete government workflow.

---

### STEP 2 — Confirm that the UDISE result exists in the school record

The OGR record is checked after UDISE processing.

The important observed change is:

- **UID is now populated.**

The UID shown in the workflow belongs to the student and is the UDISE identifier produced/recorded through the UDISE process.

The automation must read the actual value from the spreadsheet; it must never hardcode an example UID.

Example values appearing in the recorded workflow are only examples of the format and are not reusable constants.

---

### STEP 3 — Confirm that PEN is still a separate pending field

At this handoff point, the PEN field has **not yet been completed by the normal PEN workflow**.

Depending on the student's condition and processing stage, the OGR PEN cell can appear as:

- `ND`,
- `IMPORT`,
- blank/pending, or
- another explicitly defined pending state.

The automation must not interpret any of these as proof that PEN processing is finished.

For the normal New PEN workflow, `ND` is an expected intermediate state before the National UDISE+ process is completed.

Later, after the National UDISE+ completion flow, the PEN spreadsheet may legitimately become:

```text
PEN = ND
PEN row = GREEN
```

That later state is a **successful completed PEN state**, because the portal may return `Not Available` / `NA`, which is represented as `ND` in the spreadsheet.

---

## 33.4 Spreadsheet color/state transition at the handoff

This is one of the most important rules in the entire project.

### UDISE sheet

After verified UDISE completion:

```text
UDISE row BEFORE completion
        ↓
UDISE process completed
        ↓
Success verified
        ↓
ENTIRE UDISE ROW = GREEN
```

The automation must color the **entire UDISE row GREEN**, not merely the UID/UDISE cell.

### OGR

At the same point:

```text
OGR UID = populated
OGR PEN = still pending / ND / IMPORT / blank as applicable
OGR row color = UNCHANGED
```

**Do not turn the OGR row green because UDISE succeeded.**

This distinction must be implemented as a hard business rule, not as a visual preference.

### PEN sheet

The PEN row must NOT be marked GREEN merely because UDISE succeeded.

The PEN row becomes GREEN only after its own PEN branch reaches a verified successful completion state.

---

## 33.5 Exact automation checkpoint after UDISE

The automation should create an internal checkpoint equivalent to:

```text
UDISE_STATUS = VERIFIED_COMPLETE
UID = actual 18-digit project-defined UDISE value
OGR_UID = populated/verified
OGR_PEN = pending state
UDISE_ROW = GREEN
OGR_ROW = unchanged
PEN_STATUS = NOT_YET_COMPLETE
```

The exact internal variable names are implementation choices; the state meaning is mandatory.

This checkpoint should be persisted in SQLite/logs so that the application can resume safely if the program closes before PEN processing begins.

---

## 33.6 What must be checked before starting PEN

Before the automation opens or starts the PEN workflow, it should verify all of the following:

### Check A — Student identity

Confirm that the student being processed is the same student represented by the UDISE and PEN spreadsheet rows.

Minimum identity context should include, where available:

- Student name
- Father's name
- Mother's name
- DOB
- Class
- Aadhaar, where permitted/required by the workflow
- GR/admission number

Do not silently switch to another student because a search result happens to be first in a list.

### Check B — UDISE row

Confirm the entire UDISE row is GREEN.

If the row is not GREEN, normal PEN processing must not be treated as safely completed.

### Check C — UID

Confirm the UID/UDISE field contains the actual student value.

Do not use the presence of a UID alone as proof of full UDISE completion; the GREEN row and verified completion state are also required.

### Check D — PEN state

Determine whether the student falls into:

1. New UDISE + New PEN
2. New UDISE + PEN Import
3. UDISE already available/imported + New PEN
4. UDISE + PEN both imported

Do not infer the branch only from whether the PEN cell happens to be blank. Use the project's explicit entry-condition rules.

---

## 33.7 What the automation must NOT do at this point

The automation must NOT:

- mark the PEN row GREEN,
- mark the OGR row GREEN,
- assume PEN exists because UID exists,
- overwrite a valid PEN with ND,
- replace an import state with a New Entry state without the import rules,
- run the ND reconciliation process automatically merely because PEN is currently ND,
- re-run the entire UDISE workflow if the verified UDISE checkpoint already exists,
- process an already-GREEN UDISE row again by default,
- select an ambiguous student match automatically.

---

## 33.8 Relationship to the later ND process

There are two different meanings of `ND` that must not be confused:

### During the normal New PEN workflow

The National UDISE+ portal can initialize/save the student and return a state in which PEN is not available. The spreadsheet representation is `ND`.

If the rest of the PEN profile is successfully completed and the portal reports completion, then:

```text
PEN = ND
PEN row = GREEN
```

is valid.

### During later ND reconciliation

A separate later operation can revisit students whose PEN is ND and check the National UDISE+ Student Database. The operator:

1. selects the correct class first,
2. searches the student name,
3. matches the correct student,
4. reads the current PEN,
5. if an actual 11-digit PEN exists, updates the PEN sheet and OGR,
6. if no actual PEN exists, leaves ND unchanged.

This later reconciliation is **not the same operation as the immediate post-UDISE handoff**.

---

## 33.9 Failure handling at the handoff

If the automation reaches this checkpoint and finds:

### Case 1 — UID missing

Do not continue as a verified UDISE success.

Action:

- stop the normal handoff,
- log the student,
- mark for retry/manual review,
- inspect the UDISE process/result.

### Case 2 — UID exists but UDISE row is not GREEN

Do not assume completion.

Reason:

UID presence is not sufficient evidence of complete UDISE profile completion.

Action:

- verify UDISE portal/profile completion,
- do not mark the row GREEN merely because UID exists.

### Case 3 — UDISE row GREEN but UID missing

This is an inconsistent spreadsheet state.

Action:

- do not continue blindly,
- log inconsistency,
- send to manual review.

### Case 4 — PEN already has a real 11-digit value

Do not replace it with ND.

Determine whether the student is already completed/imported according to the entry-condition rules and skip unnecessary reprocessing.

### Case 5 — PEN is ND

Do not automatically call this an error.

Determine whether this is:

- a pending New PEN state, or
- a completed PEN state where the portal returned no PEN, or
- a later ND reconciliation candidate.

The distinction comes from the workflow/status context, not the text `ND` alone.

---

## 33.10 Automation state-machine representation

The handoff should be represented conceptually as:

```text
[UDISE PROCESSING]
       |
       | full relevant profile completed
       v
[UDISE SUCCESS VERIFICATION]
       |
       | success confirmed
       v
[UDISE ROW GREEN]
       |
       | UID verified in OGR
       v
[POST-UDISE CHECKPOINT]
       |
       +--> PEN already valid/completed? ---- YES ---> SKIP/RECORD COMPLETE
       |
       +--> PEN Import condition? ----------- YES ---> IMPORT BRANCH
       |
       +--> New PEN condition? -------------- YES ---> NEW PEN BRANCH
       |
       +--> ambiguous/inconsistent ---------- YES ---> MANUAL REVIEW
```

This checkpoint is therefore the bridge between the Gujarat UDISE workflow and the National UDISE+ PEN workflow.

---

## 33.11 Source-evidence boundary — do not invent missing clicks

The recording establishes the **post-UDISE record state** described above. It does not provide enough preserved detail in the current context file to claim an exact click-by-click browser sequence for every action that occurred before the recording's displayed state.

Therefore, the context file must distinguish:

- **Observed/confirmed:** UID populated after UDISE; PEN remains separate/pending; OGR color remains unchanged; the next process is PEN according to the applicable condition.
- **Engineering rule:** the automation must verify these states before continuing.
- **Not established by this recording:** exact browser click coordinates, exact DOM selectors, exact timestamps, and any UI transition not explicitly recorded in the surviving analysis.

A future developer must NEVER invent a selector, button name, popup, or portal message and label it as video-observed.

---

## 33.12 Developer implementation contract

Implement this section as a formal checkpoint, not as a comment.

The automation must be able to answer:

```text
Who is the student?
Which sheet row is being processed?
Did UDISE actually complete?
How was UDISE success verified?
Is the UDISE row GREEN?
What UID was produced?
What is the current PEN state?
Which of the four entry conditions applies?
What PEN branch should run next?
What happens if the state is inconsistent?
```

If these questions cannot be answered from the stored state/log before the next browser action, the automation must pause rather than guess.

---

# 34. NATIONAL UDISE+ / PEN PORTAL

Source:

`PEN ENTRY.mp4`

Observed portal:

**UDISE+ Student Database Management System**

Visible URL structure:

`sdms.udiseplus.gov.in/g2/#/school/...`

Do not hardcode the exact URL path from the recording; use the current configured portal URL.

---

# 35. NATIONAL PORTAL SCHOOL CONTEXT

The recorded header showed:

- UDISE Code: `24224100067`
- Category: `1 - Primary`
- Type: `3 - Co-educational`
- Management: `5 - Pvt. Unaided (Recognized)`
- Class: `Nursery/KG/PP3 - 5`
- School: `SATYAM STARS INTERNATIONAL SCHOOL`
- Current Academic Year: `2026-27`

These are portal context values, not values to hardcode into every student.

---

# 36. NATIONAL PORTAL USER

The recording showed a school user:

**SUNIL PRADHAN**

Do not store or hardcode login credentials in code.

Use secure runtime authentication.

---

# 37. PEN — STUDENT NEW ENTRY / INITIALIZATION

The new PEN workflow creates/initializes a student.

Example:

**AISHA TOFAN BISOYI**

Class:

**LKG/KG1/PP2**

Section:

**A**

DOB:

**02/01/2022**

The source spreadsheet provided the student information used to populate the profile.

---

# 38. PEN — NEW STUDENT GENERAL PROFILE FIELDS

The national profile displayed numbered fields.

Visible fields included:

### 4.1.6
Guardian's Name

### 4.1.7
AADHAAR Number of Student

### 4.1.8
Name of Student as per/in AADHAAR Card

### 4.1.9
Admission Date (DD/MM/YYYY) in Present School

### 4.1.10(a)
Mobile Number of Student/Parent/Guardian

### 4.1.10(b)
Alternate Mobile Number

### 4.1.11
Whether CWSN?

There are earlier fields above the captured screen for:

- student name,
- mother's name,
- father's name,
- surname,
- other demographic fields.

The portal visibly uses green checkmarks to indicate accepted/validated fields.

---

# 39. PEN — AADHAAR DEMOGRAPHIC CONSENT

A significant event was recorded.

When Aadhaar information is used, the portal displayed:

**CONSENT FOR DEMOGRAPHIC AUTHENTICATION**

The dialog stated that the Head of School/authorized staff member declares that the natural/legal guardian has given consent to provide Aadhaar for demographic authentication.

Button:

**I Agree**

This is a legally meaningful confirmation.

Automation design must treat this as a **controlled/manual confirmation point unless the school explicitly authorizes the automation to perform it under its established consent procedure**.

Do not blindly click legal-consent dialogs merely because they appear.

---

# 40. PEN — AADHAAR VALIDATION

After Aadhaar is entered/validated, the field can display:

- masked Aadhaar number,
- green checkmark,
- name as per Aadhaar,
- green checkmark.

Example:

`********4825`

and:

`AISHA BISOYI`

The automation should not require the full Aadhaar to be visible in the UI.

---

# 41. PEN — GENERAL PROFILE ADDRESS

The profile contains:

### 4.1.9(a)
Address

Example:

`183, SHREE RAMNAGAR, BAMROLI ROAD, PANDESARA, Surat, Gujarat, 394221`

### 4.1.9(b)
Pincode

Example:

`394221`

### 4.1.10(a)
Mobile number

Example:

`9337302202`

### 4.1.10(b)
Alternate mobile

May be blank.

### 4.1.11
Contact email ID

May be blank.

### 4.1.12
Mother Tongue of Student

The dropdown is sourced from official census data according to the portal's displayed note.

Example selected value:

`114-ODIA - Odia`

---

# 42. PEN — SOCIAL / RELIGION / BPL / EWS / CWSN

Observed fields include:

### 4.1.13
Social Category

Example:

`1 - GENERAL`

### Religion

A dropdown was opened showing options including:

- 1-Muslim
- 2-Christian
- 3-Sikh
- 4-Buddhist
- 5-Parsi
- 6-Jain
- 7-NA

### 4.1.15
Whether BPL beneficiary?

Yes/No

### 4.1.15(a)
Whether Antyodaya Anna Yojana (AAY) beneficiary?

Yes/No

### 4.1.16
Whether belongs to EWS / Disadvantaged Group?

Yes/No

### 4.1.17
Whether CWSN?

Yes/No

The Aisha example showed CWSN = No.

---

# 43. PEN — PROFILE HEADER STATUS

After initialization and while editing the profile, the portal header showed:

**Permanent Education Number - Not Defined**

plus:

**Student AADHAAR Verified**

and:

**CWSN - No**

and:

**Impairment Type - NA**

This is one of the strongest pieces of evidence for the NA/ND distinction.

---

# 44. PEN — FOUR PROFILE STAGES

The national portal visibly organizes the student's record into four stages:

1. **General Profile**
2. **Enrolment Profile**
3. **Facility Profile**
4. **Profile Preview**

The automation must progress through these stages and verify each required section.

---

# 45. PEN — INITIALIZATION SUCCESS DIALOG

After the new student is initialized/saved, the portal displays a notification:

**The Student has been initialised/Saved Successfully.**

It shows:

- Student Name
- Class
- Section

Buttons:

- `Add New Student`
- `Go to New Entry List`
- `Fill General Profile`

For the demonstrated student:

- Student Name: `AISHA TOFAN BISOYI`
- Class: `LKG/KG1/PP2`
- Section: `A`

This dialog is an explicit success checkpoint.

---

# 46. PEN — ENROLMENT PROFILE

The Enrolment Profile contains fields such as:

### 4.2.1
Admission Number in Present School

Example source:

`P089`

### 4.2.2
Admission Date in Present School

Example:

`18/05/2026`

### Class/Section Roll Number

A field is visible.

### 4.2.3(a)
Medium of Instruction

Example:

`19-English`

### 4.2.3(b)(i)
Languages Group Studied by the Student

Example:

`English`

The portal shows the selected language group separately.

### Foreign Language

A separate area may be disabled when not applicable.

### 4.2.3(c)
Subjects (Other than Language) opted by the Student

- Mandatory/General Subjects
- Additional Subjects
- Co-Curricular Subjects

---

# 47. PEN — CLASS/ACADEMIC OPTIONS

The Enrolment screen includes class-related dropdowns.

A captured dropdown showed:

- PP-3
- PP-2
- PP-1
- I
- II
- III
- IV
- V
- VI
- VII
- VIII
- IX
- X
- XI
- XII

This is evidence that class-dependent options are dynamically controlled by the portal.

---

# 48. PEN — PREVIOUS ACADEMIC STATUS

Observed field:

**4.2.5(a) Status of student in Previous Academic Year of Schooling**

Example:

`1-Studied at Current/Same School`

There is also a class-selection field for previous class.

---

# 49. PEN — RTE / PREVIOUS RESULT

Observed:

### 4.2.6(a)
Whether Admitted under Section 12C of RTE Act?

Yes/No

### 4.2.6(b)
Amount Claimed from Government for RTE entitlement

May be disabled/non-applicable depending on selection.

### 4.2.7(a)
In previous class studied — Result of the examination

Dropdown.

### 4.2.7(b)
Marks obtained in previous class (Percentage)

Numeric field.

### 4.2.8
No. of days student attended school in previous academic year

Numeric field.

---

# 50. PEN — FACILITY PROFILE

The third stage:

**Facility Profile**

Observed fields include:

### 4.3.3
Did the student appear in any State Level Competitions / National Level Competitions / Olympiads?

Yes/No

### 4.3.4
Does the Student Participate in?

- NCC — Yes/No
- NSS — Yes/No
- Scouts and Guides — Yes/No

### 4.3.5(a)
Student's Height (in CMS)

Example:

`105`

### 4.3.5(b)
Student's Weight (in KGS)

Example:

`45`

### 4.3.6
Approximate Distance of student's residence to school

Example:

`1 - Less than 1 km`

This field was shown as **required** when left unselected.

### 4.3.7
Completed Highest Education Level of Mother/Father/Legal Guardian

Dropdown.

---

# 51. PEN — FACILITY SAVE

The Facility screen includes:

- Back
- Save
- Next

The portal can show red required-field indicators when mandatory information is missing.

Therefore the automation should detect validation failures before attempting to continue.

---

# 52. PEN — PROFILE PREVIEW / FINAL COMPLETION

At the end, the portal displays the completion state.

The final modal says:

**Data completion is complete.**

Buttons:

- `Okay`
- `Back to Student Dashboard`

This is the strongest demonstrated final completion signal.

---

# 53. PEN — RETURN TO PEN SHEET

After portal completion, the user returns to:

**PEN_Entry_(National)**

The student's PEN cell is set to:

`ND`

The entire row is changed to:

**GREEN**

This is a spreadsheet-side completion operation.

---

# 54. PEN GREEN DOES NOT MEAN ACTUAL PEN EXISTS

Very important:

A row can be:

```text
PEN = ND
ROW = GREEN
```

This is a valid completed **New PEN Entry** state.

It means:

- profile creation/completion has been performed,
- but the actual PEN is not yet available.

It does NOT mean that the automation failed.

---

# 55. ND MANUAL CHECK — DEDICATED VIDEO

Source:

`5 ND MANUAL UPDATE.mp4`

Duration:

~112 seconds.

Purpose:

Find actual PEN numbers for students whose spreadsheet currently says:

`ND`

---

# 56. ND CHECK — SOURCE SHEET STATE

The recording showed the OGR with columns including:

- AY
- NAME
- STD
- DOE
- AADHAR
- UID
- PEN
- APAAR
- DOCUMENTS PENDING

Rows contained multiple `ND` values in the PEN column.

This establishes that the ND-check process uses the OGR/student record as part of reconciliation.

---

# 57. ND CHECK — PORTAL SEARCH

The process uses the national UDISE+ Student Database.

The recording demonstrates:

1. Open UDISE+ Student Database.
2. Select the class first.
3. Use the student search field.
4. Search by student name.
5. Locate the matching student row.
6. Read the PEN displayed by the portal.

This is **class-first, then name-search**.

Do not search the whole school without first selecting the appropriate class.

---

# 58. ND CHECK — CLASS DROPDOWN

The portal student list showed a class selector.

Example class:

`LKG/KG1/PP2`

Section:

`All` or a selected section.

The search box is on the right.

---

# 59. ND CHECK — STUDENT LIST COLUMNS

The portal's student list showed:

- Class/Grade
- PEN (Permanent Education Number)
- Student's Name
- Gender
- Date of Birth
- Entry Status
- Last Updated (On/By)

Action/status buttons visible include:

- GP = General Profile
- EP = Enrolment Profile
- FP = Facility Profile
- profile/document-style icon

This allows the operator to identify the correct student and read the current PEN.

---

# 60. ND CHECK — EXAMPLE

The video demonstrated an actual PEN becoming available.

The spreadsheet initially contained:

`ND`

After portal search, an actual 11-digit PEN was found:

`23613114903`

The spreadsheet was then updated:

`ND → 23613114903`

This was visible in OGR.

---

# 61. ND CHECK — SECOND EXAMPLE

Another student was searched and an actual PEN was shown:

`23584566926`

The OGR was updated from the pending state to the actual PEN.

Therefore the ND reconciliation function must support repeated students, not just one example.

---

# 62. ND CHECK — IF NO PEN EXISTS

If the portal still shows:

`NA`

or otherwise has no actual PEN:

**KEEP THE SPREADSHEET VALUE AS `ND`.**

Do not invent a temporary number.

Do not copy a school ID.

Do not use UID as PEN.

---

# 63. ND CHECK — OGR UPDATE

The ND-check recording establishes an important detail that was previously uncertain:

When an actual PEN becomes available, the OGR PEN cell is updated with the actual 11-digit PEN.

Thus the reconciliation process can include:

```text
PEN sheet: ND → actual PEN
OGR: ND/blank → actual PEN
```

The exact PEN-sheet row-update timing for every scenario should still be treated as part of the final reconciliation implementation.

---

# 64. IMPORTANT CORRECTION TO EARLIER HANDOFF

The earlier master document said that the exact timing of the OGR PEN update was not fully established.

The dedicated ND-check recording now provides additional evidence:

**OGR is definitely updated with the actual PEN during the ND reconciliation process.**

Therefore the final automation specification should include OGR reconciliation as part of the ND-check operation.

---

# 65. PEN PORTAL ENTRY STATUS

The portal can display statuses such as:

- `Not Started`
- `In-Progress`
- `Completed`

The list also shows the GP/EP/FP stage indicators.

This is useful for automation.

Example:

- New student can show `Not Started`.
- A partially completed record can show `In-Progress`.
- A fully completed record can show `Completed`.

Automation should use these statuses to avoid unnecessary re-entry.

---

# 66. PEN ROW GREEN + PORTAL STATUS

The spreadsheet green state and portal `Completed` state are related but not identical.

Portal:

`Completed`

then spreadsheet:

`PEN = ND`
`Entire PEN row = GREEN`

This is the observed New PEN workflow.

---

# 68. CONDITION 2 — EXPECTED STRUCTURE

### New UDISE + PEN Import

The UDISE side is already known.

Therefore:

```text
Student
  ↓
New UDISE workflow
  ↓
UDISE completed
  ↓
PEN already exists/imported
  ↓
PEN Import / Other State workflow
  ↓
major changes as required
```

**PEN Import — Other School ACTIVE: DOCUMENTED FROM RECORDING.** The
exact screens, buttons, and business-routing logic are recorded in
"PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW" at the end
of this document. **PEN Import — successful/Dropbox outcome: BUSINESS
RULE DEFINED, CLICK-LEVEL WORKFLOW NOT DEMONSTRATED** — no recording shows
this path; do not invent it.

---

# 69. CONDITION 3 — EXPECTED STRUCTURE

### UDISE Import + New PEN

Expected conceptual flow:

```text
Student
  ↓
UDISE already available/imported
  ↓
No new UDISE creation unless import workflow requires an update
  ↓
New PEN workflow
  ↓
PEN completion
```

The exact UDISE import steps are pending.

---

# 70. CONDITION 4 — EXPECTED STRUCTURE

### UDISE Import + PEN Import

Expected conceptual flow:

```text
Student
  ↓
UDISE Import
  ↓
PEN Import
  ↓
required updates/changes
  ↓
completion/status updates
```

Exact import behavior is pending.

---

# 71. DO NOT ASSUME IMPORT = NEW ENTRY

Import is not merely "New Entry with fewer fields."

The user explicitly said:

- Condition 2 has **major changes**
- Other State is involved
- Import-specific workflow must be documented separately

Therefore the coding agent must implement import as a distinct workflow branch.

---

# 72. SPREADSHEET STATUS VALUES

Observed operational values include:

- blank
- `ND`
- `IMPORT`
- actual PEN
- `GREEN` row formatting

The UDISE workbook also contains `REMARK` values such as:

- `REQUEST SENT`

The PEN import workbook contains:

- `ACTIVE`
- `IMPORT PENDING`

The exact meaning of every status value must be determined before automation changes it.

Do not equate every non-green/non-empty status with pending work.

---

# 73. DATA MATCHING

Potential student matching fields observed across files include:

- Student Name
- Father's Name
- Mother's Name
- Surname
- DOB
- Aadhaar
- Class
- GR No / admission number
- Mobile numbers
- UID/UDISE
- PEN

For imports, matching may also involve:

- existing PEN
- previous school
- previous school UDISE
- state
- district
- block

The final matching hierarchy has not yet been explicitly specified.

The automation must not silently match students on name alone when multiple candidates exist.

---

# 74. PORTAL SEARCH STRATEGY

Normal structured fields should be handled with:

- DOM selectors,
- labels,
- option values,
- accessible names,
- table rows,
- stable attributes.

Do not rely primarily on:

- mouse coordinates,
- screenshots,
- OCR,
- pixel positions.

The videos show that the portals contain standard HTML controls.

---

# 75. OCR REQUIREMENT

Normal workflow:

**No OCR required.**

The portal has structured:

- input fields,
- dropdowns,
- buttons,
- tables,
- modals,
- status labels.

OCR should only be considered for an exceptional screen where no reliable DOM-accessible value exists.

It is not the default architecture.

---

# 76. AUTOMATION STACK DISCUSSED

Proposed stack:

### Python
Main application language.

### PySide6
Windows desktop UI.

### Playwright
Browser automation.

### Google Sheets API
Google Sheets read/write.

### SQLite
Local state, logs, checkpoints, retry information.

### PyInstaller
Package as Windows `.exe`.

---

# 77. PROPOSED APPLICATION ARCHITECTURE

Conceptually:

```text
                    ┌──────────────────────┐
                    │   PySide6 Desktop UI │
                    └──────────┬───────────┘
                               │
                  ┌────────────▼────────────┐
                  │ Workflow / State Engine │
                  └───────┬────────┬────────┘
                          │        │
                 ┌────────▼─┐   ┌──▼─────────┐
                 │ Sheets    │   │ Playwright │
                 │ Adapter   │   │ Browser    │
                 └─────┬─────┘   └────┬──────┘
                       │              │
               ┌───────▼──────┐ ┌─────▼─────────────┐
               │ Google Sheets│ │ Gujarat UDISE     │
               │ OGR/UDISE/PEN│ │ + UDISE+ National │
               └──────────────┘ └───────────────────┘
                          │
                   ┌──────▼──────┐
                   │ SQLite State│
                   │ + Logs      │
                   └─────────────┘
```

---

# 78. STATE-DRIVEN DESIGN

Do not create one huge macro.

The automation should have explicit states such as:

```text
READ_SHEETS
↓
VALIDATE_STUDENT
↓
DETERMINE_CLASS_ROUTE
↓
DETERMINE_ENTRY_CONDITION
↓
RUN_UDISE_BRANCH
↓
VERIFY_UDISE
↓
RUN_PEN_BRANCH
↓
VERIFY_PEN
↓
UPDATE_SHEETS
↓
LOG_SUCCESS
```

And separate:

```text
CHECK_ND_PEN
```

for later reconciliation.

---

# 79. CONDITION DECISION TREE

```text
                         STUDENT
                            │
                            ▼
                  Determine UDISE state
                            │
              ┌─────────────┴─────────────┐
              │                           │
            NEW                         IMPORT
              │                           │
              ▼                           ▼
       Determine PEN state         Determine PEN state
              │                           │
        ┌─────┴─────┐               ┌─────┴─────┐
        │           │               │           │
       NEW        IMPORT           NEW        IMPORT
        │           │               │           │
        ▼           ▼               ▼           ▼
      COND 1      COND 2           COND 3      COND 4
```

---

# 80. COMPLETION RULE — UDISE

A UDISE student should be considered complete only after:

1. correct student selected/created,
2. birth/CTS data accepted,
3. required Manage Student profile sections completed,
4. required conditional fields handled,
5. Save Student succeeds,
6. portal state is successfully saved,
7. relevant UDISE spreadsheet record is updated,
8. **entire UDISE row is GREEN**.

---

# 81. COMPLETION RULE — NEW PEN

A New PEN student should be considered complete only after:

1. correct class selected,
2. student initialized,
3. initialization success confirmed,
4. General Profile completed,
5. Enrolment Profile completed,
6. Facility Profile completed,
7. Profile Preview/final workflow completed,
8. portal shows:
   **Data completion is complete.**
9. PEN availability inspected,
10. if actual PEN unavailable, spreadsheet gets `ND`,
11. **entire PEN row becomes GREEN**.

---

# 82. COMPLETION RULE — ND CHECK

An ND check is complete for a student after:

1. student has PEN `ND`,
2. correct class selected,
3. student searched,
4. correct student matched,
5. current portal PEN read,
6. if actual 11-digit PEN exists:
   - update PEN spreadsheet,
   - update OGR PEN,
7. otherwise:
   - retain `ND`,
8. log check result.

The exact green-row behavior during later ND reconciliation is not separately demonstrated as a new color change; do not invent one.

---

# 83. LEGAL / HUMAN-CONFIRMATION POINTS

The national portal displayed an Aadhaar demographic-authentication consent dialog.

The eventual application should support a manual intervention mode:

```text
Automation reaches consent dialog
        ↓
Pause
        ↓
User confirms authorized consent
        ↓
Resume
```

Do not automatically make legal declarations unless the school has explicitly authorized that operation and the process is compliant with its consent procedure.

---

# 84. SECURITY REQUIREMENTS

Never hardcode:

- government portal passwords,
- Google passwords,
- OTPs,
- Aadhaar values unnecessarily,
- other credentials.

Do not commit credentials to GitHub.

Use:

- secure configuration,
- runtime login,
- environment variables/OS credential storage where appropriate,
- protected local state.

---

# 85. GOOGLE SHEETS API ARCHITECTURE

The intended process is:

```text
Google Sheets
      ↓
Python batch read
      ↓
records in memory
      ↓
Playwright processes students one by one
      ↓
collect results
      ↓
Google Sheets batch update
```

Avoid making one API call per cell whenever possible.

Batch reads/writes should be used.

---

# 86. GOOGLE CLOUD ROLE

Google Cloud is for the Google Sheets API authorization/configuration layer.

It is not intended to host the desktop application.

The proposed first version can run locally on Windows.

No cloud server is required merely to execute the browser automation.

---

# 87. ERROR HANDLING

The automation must recognize at least these classes of failure:

- login failure
- wrong class
- student not found
- duplicate student match
- validation error
- required field missing
- portal timeout
- network failure
- session expiration
- save failure
- unexpected modal
- portal status not changed
- spreadsheet write failure
- import record mismatch

A failed student should not be marked GREEN.

---

# 88. RETRY / RESUME

The application should support:

- Retry current student
- Skip current student
- Resume from last successful checkpoint
- Save failure screenshot
- Save error message
- Preserve sheet state
- Avoid reprocessing already-completed green rows

---

# 89. IMPORTANT: GREEN ROWS MUST NOT BE REPROCESSED

A green UDISE/PEN row means the corresponding workflow is completed.

Therefore:

```text
GREEN → SKIP
```

unless the user explicitly chooses a reprocess/repair function.

---

# 90. IMPORTANT: ND IS NOT A FAILURE

```text
PEN = ND
```

does not mean:

```text
PEN workflow failed
```

It means the new profile workflow can be complete while the actual PEN has not yet been generated.

Therefore:

```text
PEN = ND + GREEN ROW
```

is a valid state.

---

# 91. IMPORTANT: IMPORT IS NOT PENDING BY DEFAULT

A student with an import state must be routed to the correct import workflow.

Do not automatically run New Entry because the student is not green.

---

# 92. IMPORTANT: PORTAL `NA` IS NOT EXCEL `NA`

Portal:

`NA = Not Available`

School spreadsheet:

`ND = Not Defined`

The automation must preserve this mapping.

---

# 93. IMPORTANT: UDISE UID IS NOT PEN

Do not copy:

- UID into PEN
- PEN into UID

UID/UDISE:

**18 digits**

PEN:

**11 digits**

---

# 94. IMPORTANT: UDISE SUCCESS IS NOT JUST UID GENERATION

The UDISE form has multiple sections and conditional data.

Completion means the applicable profile has been saved successfully.

---

# 95. IMPORTANT: PEN SUCCESS IS NOT JUST STUDENT INITIALIZATION

Initialization is only one stage.

After initialization, the student must continue through:

```text
General Profile
→ Enrolment Profile
→ Facility Profile
→ Profile Preview
```

until final completion is confirmed.

---

# 96. VIDEO TIMELINE — GOOGLE SHEET

Approximate observations:

### 0–20 sec
Browser/Google environment.

### ~20–40 sec
UDISE/PEN source student tables visible.

### ~40–60 sec
OGR/new student row structure visible.

### ~60–100 sec
Student data and sheet movement demonstrate the staged OGR entry concept.

Core lesson:

> OGR is entered in stages and is connected to the government-entry process.

---

# 97. VIDEO TIMELINE — GUJARAT UDISE

Approximate timeline from the analyzed 10:44 recording:

### ~0–150 sec
Portal navigation/login/student-management context.

### ~160 sec
`STUDENT NEW ENTRY` visible.

### ~160–190 sec
Birth information/CRS-RGI route.

### ~180 sec
Gender dropdown visible.

### ~190–220 sec
Manual birth-entry route opened.

### ~200–220 sec
State/district/taluka/city/village and birth certificate fields.

### ~220 sec
Dependent location dropdowns opened.

### ~300 sec
OGR visible with Aisha row.

### ~320–400 sec
Manual CTS/new-student details completed.

### ~420–520 sec
Manage Student → Personal tab.

### ~540–580 sec
Education tab and class/education dropdowns.

### ~600 sec
Bank tab.

### ~620 sec
Health/CWSN fields.

The final part demonstrates that UDISE is a multi-tab student profile process.

---

# 98. VIDEO TIMELINE — AFTER UDISE BEFORE PEN

Approximate:

### ~0–20 sec
UDISE student-management context.

### ~20–50 sec
Student record/table.

### ~60–80 sec
OGR visible with UID and PEN states.

### ~90–110 sec
OGR further updated/verified.

Core confirmed behavior:

- UID is populated.
- PEN remains a separate state.
- OGR color is not the UDISE/PEN green-completion indicator.

---

# 99. VIDEO TIMELINE — PEN ENTRY

Approximate:

### ~0–20 sec
Google/UDISE+ login context.

### ~40–80 sec
PEN sheet and UDISE+ student dashboard.

### ~100–140 sec
Student profile/new-entry area.

### ~140–160 sec
General Profile fields.

### ~160 sec
Aadhaar consent dialog.

### ~175 sec
Return/sheet context.

### ~190 sec
Initialization success dialog.

### ~205–230 sec
General Profile/address/Aadhaar fields.

### ~220 sec
Religion/category/BPL/EWS/CWSN fields.

### ~240 sec
Enrolment Profile.

### ~260 sec
Medium/languages/subjects.

### ~280 sec
Previous class/status/RTE/result fields.

### ~300–325 sec
Facility Profile.

### ~335 sec
`Data completion is complete.`

### ~340–360 sec
PEN sheet/UDISE sheet/OGR updates.

### ~370 sec
PEN cell shown as `ND`, row green.

---

# 100. VIDEO TIMELINE — ND MANUAL UPDATE

Approximate:

### ~0–30 sec
OGR/PEN sheet context.

### ~40 sec
UDISE+ dashboard.

### ~50–70 sec
Class/student search workflow.

### ~80 sec
Student list after class selection.

### ~90 sec
OGR shows actual PEN update for one student.

### ~100 sec
Another student search.

### ~110 sec
OGR shows another actual PEN.

Core lesson:

> ND checking is a later reconciliation operation, separate from New PEN creation.

---

# 101. EXAMPLE STUDENT DATA FLOW — AISHA

This example ties the videos together.

## OGR / source

Aisha's record includes:

- Name: AISHA BISOYI
- Class: SR KG
- DOB: 02/01/2022
- Father: TOFAN
- Mother: PRIYANKA
- Surname: BISOYI
- Mobile: 9337302202
- Aadhaar: 617750014825
- Admission/PR: P091

## UDISE

Birth information is entered/verified.

CTS record is created.

Manage Student profile is completed.

UID is generated/recorded.

## PEN

National student is initialized.

Portal shows:

`Permanent Education Number - Not Defined`

Profile is completed.

Final modal:

`Data completion is complete.`

PEN sheet:

`ND`

Entire PEN row:

GREEN.

## Later

If actual PEN appears, ND checking replaces:

`ND → actual 11-digit PEN`

and OGR is also updated with the actual PEN.

---

# 102. AUTOMATION SHOULD USE DATA, NOT EXAMPLES

The example names/numbers above exist only to explain the process.

The automation must dynamically read:

- name,
- class,
- DOB,
- parent names,
- Aadhaar,
- address,
- mobile,
- admission date,
- GR/PR,
- UDISE,
- PEN,
- status,
- phase,
- import condition.

No example student should be hardcoded.

---

# 103. AUTOMATION SHOULD DETECT CURRENT PORTAL STATE

When opening a student, the automation should inspect whether the portal says:

- Not Started
- In-Progress
- Completed
- Permanent Education Number — Not Defined
- actual PEN
- Aadhaar verified
- CWSN state
- validation error

and choose the appropriate continuation path.

This is safer than replaying every click blindly.

---

# 104. FIELD MAPPING REQUIREMENT

Before coding, create a mapping layer:

```text
SOURCE SHEET FIELD
       ↓
NORMALIZED STUDENT OBJECT
       ↓
PORTAL FIELD
```

Example:

```text
OGR.NAME
UDISE.Student Name
PEN.Student Father Surname
        ↓
student.full_name
        ↓
Portal Student Name
```

Likewise:

```text
DOB → normalized DOB → portal DOB
AADHAAR → normalized Aadhaar → portal Aadhaar
MOBILE 1 → primary mobile
MOBILE 2 → alternate mobile
```

This is necessary because the same concept appears under different spreadsheet column names.

---

# 105. DATA NORMALIZATION

The final application should normalize:

- dates,
- phone numbers,
- Aadhaar,
- PEN,
- UID,
- class names,
- gender,
- names,
- missing values,
- `-`,
- `ND`,
- `NA`,
- blank cells.

But normalization must never silently change a student's actual value.

Example:

```text
Portal NA
≠
Spreadsheet ND
```

The mapping is intentional.

---

# 106. DATE HANDLING

The source files contain mixed date representations.

Examples:

- `02/01/2022`
- `18/05/2026`
- Excel datetime values
- strings
- Google Sheets displayed dates

The automation should normalize internally to a real date object and format according to each portal's required display format.

Do not rely on the displayed Google Sheets format.

---

# 107. CLASS NORMALIZATION

Class names may appear as:

- JR KG
- SR KG
- SR.KG
- Balvatika
- 1st
- LKG/KG1/PP2
- UKG/KG2/PP1
- portal-coded values such as `102-Sr.KG`

The automation must maintain a class-mapping table rather than using literal string equality everywhere.

---

# 108. PORTAL SELECTOR STRATEGY

Preferred selector priority:

1. stable `id`
2. `name`
3. `data-*` attribute
4. accessible label
5. associated `<label>`
6. stable text
7. table row + column relation
8. CSS/XPath only when necessary

Avoid coordinate-based automation.

---

# 109. DROPDOWN STRATEGY

Dropdowns are frequent.

The automation should:

1. identify the field by label,
2. inspect available options,
3. select the correct option,
4. wait for dependent fields,
5. verify selected value,
6. continue.

Do not assume that every dropdown has the same option ordering forever.

---

# 110. DEPENDENT DROPDOWNS

Examples:

- State → District
- District → Taluka
- Taluka → City/Village
- Class → subject/class options
- CWSN Yes → disability options
- category → related fields

The automation must wait for dependent options to load before selecting the next field.

---

# 111. FILE UPLOAD

The Gujarat UDISE manual birth route contains a birth-certificate PDF upload.

The final application should support:

- selecting the correct file,
- verifying upload success,
- handling missing document,
- not uploading the wrong student's document.

Exact document-file naming/storage rules are not yet specified.

---

# 112. SESSION MANAGEMENT

Government portals may expire sessions.

The automation should detect:

- login page returned,
- session timeout,
- unauthorized state,
- unexpected logout.

It should pause/re-authenticate rather than writing incorrect spreadsheet status.

---

# 113. BATCH PROCESSING

The intended processing model is:

```text
Read batch
  ↓
Student 1
  ↓
verify
  ↓
Student 2
  ↓
verify
  ↓
...
  ↓
batch sheet update
```

Do not process hundreds of browser operations without checkpoints.

---

# 114. LOCAL LOGGING

Each student should eventually have a local log entry containing conceptually:

- timestamp
- student identifier
- name
- class
- condition
- UDISE result
- PEN result
- portal status
- sheet update status
- error
- retry count
- screenshot path if failed

Do not store unnecessary sensitive data in logs.

---

# 115. FAILURE STATE EXAMPLES

Example:

```text
AISHA
Condition 1
UDISE = SUCCESS
PEN = SUCCESS / ND
Sheet update = SUCCESS
Final state = GREEN
```

Another:

```text
STUDENT X
Condition 2
UDISE = SUCCESS
PEN IMPORT = FAILED
Reason = Student not found
Final state = NOT GREEN
Manual action required
```

The second student must not be marked complete.

---

# 116. MANUAL INTERVENTION MODE

The desktop UI should eventually have controls such as:

- Start
- Pause
- Resume
- Retry
- Skip
- Open Student
- Mark for Manual Review
- Re-check
- Check ND Students
- View Logs

Exact UI design can be decided later.

---

# 117. IMPORTANT AUTOMATION PRINCIPLE

The automation should be:

**STATE-BASED, NOT CLICK-BASED.**

Bad:

```text
click here
wait 2 sec
click there
```

Good:

```text
select class
wait until student table loaded
find exact student
verify DOB/name
open profile
fill field
verify validation
save
wait for success signal
update sheet
```

---

# 118. WHAT IS ALREADY SAFE TO IMPLEMENT LATER

After import workflows are documented, the following are already well-defined enough to design:

- sheet readers,
- student normalization,
- class routing,
- green-row skipping,
- Condition 1 workflow structure,
- New UDISE automation structure,
- New PEN automation structure,
- ND-check operation,
- batch update architecture,
- SQLite state/logging architecture,
- Playwright-based browser architecture.

---

# 119. WHAT MUST NOT BE IMPLEMENTED AS FINAL LOGIC YET

Do not finalize:

- UDISE Import
- PEN Import
- Other State PEN Import
- import matching rules
- import-specific field-change rules
- exact `IMPORT` status transition
- exact `IMPORT PENDING` completion behavior
- exact document eligibility logic
- exact PH1/PH2/PH3 selection algorithm

until the dedicated import recordings are analyzed.

---

# 120. NEXT REQUIRED RECORDINGS

Only two categories of recording remain necessary for the four-condition workflow:

### A. UDISE IMPORT
Show the exact process for a student whose UDISE is already available/imported.

### B. PEN IMPORT
Show the exact process for a student whose PEN already exists/imports, especially:

**Other State / major changes**

The New Entry videos do **not** need to be uploaded again.

---

# 121. FINAL FOUR-CONDITION STATUS TABLE

| Condition | UDISE | PEN | Status |
|---|---|---|---|
| 1 | New | New | **FULLY RECORDED** |
| 2 | New | Import | **UDISE RECORDED; PEN IMPORT PENDING** |
| 3 | Import | New | **UDISE IMPORT PENDING; PEN RECORDED** |
| 4 | Import | Import | **BOTH IMPORT WORKFLOWS PENDING** |

---

# 122. FINAL WORKFLOW MAP

```text
                         ┌───────────────────┐
                         │ Student source    │
                         │ / sheets          │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ Eligibility /     │
                         │ entry conditions  │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ Determine class   │
                         │ and ID route      │
                         └─────────┬─────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │ Determine UDISE state    │
                     └────────────┬─────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
                NEW                             IMPORT
                  │                               │
                  ▼                               ▼
         Determine PEN state              Determine PEN state
                  │                               │
          ┌───────┴───────┐               ┌───────┴───────┐
          │               │               │               │
         NEW            IMPORT           NEW            IMPORT
          │               │               │               │
          ▼               ▼               ▼               ▼
      CONDITION 1     CONDITION 2     CONDITION 3     CONDITION 4
          │               │               │               │
          └───────────────┴───────┬───────┴───────────────┘
                                  │
                                  ▼
                         Verify portal result
                                  │
                                  ▼
                         Update correct sheets
                                  │
                                  ▼
                         Record audit/log state
```

---

# 123. SEPARATE ND RECONCILIATION FLOW

```text
             PEN = ND
                 │
                 ▼
        Select correct class
                 │
                 ▼
          Search student name
                 │
                 ▼
        Match correct student
                 │
                 ▼
         Read current PEN
          /             \
       actual           none
        │                │
        ▼                ▼
  11-digit PEN          ND
        │                │
        ▼                ▼
 Update PEN sheet      Keep ND
        │
        ▼
    Update OGR
        │
        ▼
     Log result
```

---

# 124. FINAL HANDOFF INSTRUCTION TO FUTURE CHATGPT / CODING AGENT

Treat this file as the **master context** for the project.

When continuing:

1. Read this entire document first.
2. Do not ask the user to re-upload `GOOGLE SHEET.mp4`, `GUJARAT ENTRY.mp4`, `AFTER UDISE ENTRY BEFORE PEN .mp4`, `PEN ENTRY.mp4`, or `5 ND MANUAL UPDATE.mp4`.
3. Do not ask the user to re-explain the New Entry workflow.
4. Reuse the detailed New UDISE/New PEN workflow recorded here.
5. Ask only for the missing import workflow information.
6. Preserve the user's terminology:
   - OGR
   - UDISE/UID
   - PEN
   - ND = Not Defined
   - NA = Not Available
   - PH1/PH2/PH3
   - IMPORT
   - GREEN row
   - Satyam School ID
   - Block ID
7. Do not assume that ND means failure.
8. Do not assume import means new entry.
9. Do not mark rows green without verified completion.
10. Do not invent portal field values.
11. Do not invent import steps.
12. Do not hardcode credentials.
13. Do not start writing the final application until the four branches are completely specified.

---

# 125. CURRENT PROJECT STATE

## Confirmed

- Three working spreadsheets/files.
- OGR staged-entry workflow.
- Exact UDISE spreadsheet structure.
- Exact PEN spreadsheet structure.
- PEN Import Pending spreadsheet structure.
- UDISE new-entry workflow.
- UDISE birth/CRS-RGI/manual routes.
- UDISE CTS fields.
- UDISE Manage Students sections.
- UDISE Personal/Education/Bank/Scholarship & Facility/Health & CWSN structure.
- UDISE full-row green completion rule.
- New PEN workflow.
- Aadhaar verification/consent event.
- PEN General Profile.
- PEN Enrolment Profile.
- PEN Facility Profile.
- PEN Profile Preview.
- `Data completion is complete.` final signal.
- Portal `Permanent Education Number - Not Defined`.
- Portal `NA` → spreadsheet `ND`.
- PEN full-row green completion rule.
- ND checking workflow.
- Class-first/name-search method.
- Actual 11-digit PEN replacement.
- OGR actual-PEN update during ND reconciliation.
- Class-based Satyam School ID / Block ID routing.
- Proposed Python/PySide6/Playwright/Google Sheets API/SQLite/PyInstaller architecture.

## Still Pending

- UDISE Import exact workflow.
- PEN Import exact workflow.
- Other State PEN Import exact workflow.
- Condition 2 import-specific changes.
- Condition 3 import-specific changes.
- Condition 4 combined import behavior.
- Final eligibility/entry-condition rules.
- Final import matching algorithm.
- Exact exception handling for every portal error.
- Final coding-agent prompt.

---

# 126. MOST IMPORTANT SUMMARY

The system being built is NOT a simple:

```text
Excel → copy data → browser → paste data
```

It is a:

```text
STUDENT RECORD
      ↓
ENTRY CONDITION DETECTION
      ↓
CLASS / ID ROUTING
      ↓
UDISE STATE
      ↓
UDISE NEW OR IMPORT WORKFLOW
      ↓
VERIFIED UDISE COMPLETION
      ↓
PEN NEW OR IMPORT WORKFLOW
      ↓
VERIFIED PEN COMPLETION
      ↓
SHEET STATE UPDATE
      ↓
LATER ND RECONCILIATION
      ↓
ACTUAL PEN UPDATE
```

The automation must preserve the distinction between:

- **New**
- **Import**
- **NA**
- **ND**
- **Actual PEN**
- **Not Started**
- **In-Progress**
- **Completed**
- **Green row**
- **OGR unchanged color**
- **UDISE first**
- **PEN second**
- **later ND checking**

The four-condition decision engine is the central architecture.

---

# END OF MASTER EXPERT HANDOFF

---

# 127. FINAL CONTEXT FILE ADDENDUM — AUDIT CLARIFICATIONS

This section was added after a complete audit of the master handoff against the project conversation and the five already-analyzed recordings.

## 127.1 Context File status

This file is the **FINAL MASTER CONTEXT FILE** for all information established so far.

It intentionally contains:

- all confirmed workflow information from the five analyzed recordings,
- all confirmed spreadsheet structures discussed/inspected,
- all business rules explicitly established by the user,
- the automation architecture discussed so far,
- all important corrections made during the conversation,
- explicit boundaries around information that has NOT yet been observed.

The five previously analyzed recordings do **not** need to be re-uploaded merely to continue this project:

1. `GOOGLE SHEET.mp4`
2. `GUJARAT ENTRY.mp4`
3. `AFTER UDISE ENTRY BEFORE PEN .mp4`
4. `PEN ENTRY.mp4`
5. `5 ND MANUAL UPDATE.mp4`

Only the two dedicated import recordings remain necessary to complete the four-condition workflow specification:

- UDISE Import
- PEN Import / Other State

---

# 128. NON-NEGOTIABLE COMPLETION RULES

These rules are business rules, not implementation suggestions.

## 128.1 UDISE completion

**The presence of an 18-digit UDISE/UID alone does NOT mean the UDISE workflow is complete.**

The completion sequence is:

```text
UDISE/CTS student created or updated
        ↓
Required UDISE profile sections completed
        ↓
Required fields saved/validated
        ↓
Portal completion verified
        ↓
ENTIRE UDISE ROW = GREEN
```

Only after this verified UDISE completion should the normal dependent PEN workflow proceed.

The automation must never turn a UDISE row green merely because:

- a student was created,
- an 18-digit UID/UDISE appeared,
- a button was clicked,
- a page loaded,
- a form was opened,
- or no visible error appeared.

A verified completion condition is required.

---

## 128.2 PEN completion

For New PEN Entry:

```text
Student initialized
        ↓
General Profile
        ↓
Enrolment Profile
        ↓
Facility Profile
        ↓
Profile Preview / final completion
        ↓
"Data completion is complete."
        ↓
ENTIRE PEN ROW = GREEN
```

Initialization alone is NOT PEN completion.

---

## 128.3 PEN = ND can be successful

This is a valid completed state:

```text
PEN = ND
PEN ROW = GREEN
```

Interpretation:

- the New PEN profile-completion workflow has been completed,
- the actual PEN is not currently available/defined,
- the student is not automatically a failed record.

`ND` must therefore never be treated as equivalent to failure.

---

## 128.4 OGR color invariant

The OGR row color remains **UNCHANGED** during normal UDISE/PEN completion.

Do not introduce an OGR-green rule merely because UDISE or PEN has been completed.

UDISE/PEN operational green rows are separate spreadsheet completion indicators.

---

## 128.5 Green means verified completion

For UDISE and PEN operational rows:

> **GREEN = verified completion of that workflow branch.**

It does not mean merely "attempted", "opened", "initialized", "no error", or "partially entered".

---

## 128.6 Already-green rows must be skipped

If the applicable UDISE or PEN operational row is already GREEN, the automation should treat that row as completed and **skip it by default**.

Do not re-enter an already-completed green record unless the user explicitly requests a reprocessing/repair operation.

This applies regardless of whether the row belongs to PH1, PH2, or PH3.

---

# 129. OGR PARTIAL-ENTRY RULE

OGR may contain a student in a staged or partially populated state.

Examples include basic information such as:

- AY
- NAME
- STD
- MOBILE 1
- MOBILE 2
- PR

followed later by:

- DOB
- DOA
- DOE
- AADHAR
- UID
- PEN
- APAAR
- DOCUMENTS PENDING

A partially populated OGR row must **not** be interpreted as proof that government portal entry is complete.

Government-entry completion is determined by the corresponding UDISE/PEN workflow state and its verified completion indicator.

---

# 130. UDISE → PEN DEPENDENCY GATE

For the normal New/New workflow, the dependency is strict:

```text
UDISE processing
      ↓
VERIFY UDISE completion
      ↓
UDISE row GREEN
      ↓
PEN processing
```

The automation must not start the normal dependent PEN workflow simply because:

- UID exists,
- a UDISE profile page opened,
- or UDISE fields were entered.

The UDISE completion checkpoint must be satisfied first.

Import branches may legitimately skip creation of a new UDISE/PEN record because the corresponding government record already exists/imports; their exact sequencing is still pending dedicated import-video analysis.

---

# 131. NEW ENTRY WORKFLOW MUST REMAIN UNCHANGED

The addition of Import workflows must NOT rewrite or reinterpret the already-analyzed New Entry workflows.

Implementation principle:

```text
Existing New UDISE workflow
          +
Existing New PEN workflow
          +
Import-specific branches/deltas
```

Do not turn Import into a vague variation of New Entry.

The user explicitly stated that import can involve:

- an already-existing government record,
- another school,
- Other State,
- and major changes.

The exact import mechanics must come only from the dedicated import recordings.

---

# 132. IMPORT BOUNDARY — DO NOT INVENT

The following remain intentionally unresolved until the two import recordings are analyzed:

- exact UDISE Import portal navigation,
- exact UDISE Import buttons/actions,
- exact UDISE Import matching process,
- exact UDISE Import field changes,
- exact PEN Import navigation,
- exact Other State import behavior,
- exact major-change fields/actions,
- exact import confirmation dialogs,
- exact import status transitions,
- exact `IMPORT PENDING` completion behavior,
- exact import green-row behavior,
- exact combined Condition 4 behavior.

No future coding agent should invent these steps from the New Entry recordings.

---

# 133. PH1 / PH2 / PH3 OPERATIONAL INTERPRETATION

PH1, PH2, and PH3 are operational batches/phases in the observed spreadsheets.

They are **not separate data models**.

The automation should therefore use the phase/tab as an operational source/queue, while keeping the normalized student data model common.

If a row is already GREEN, it is completed regardless of which PH tab contains it.

The exact algorithm for selecting which PH to process first has not been explicitly specified and must not be invented.

---

# 134. UID / UDISE TERMINOLOGY

For this project:

```text
UID = UDISE
```

The project documentation uses these terms for the same student identifier in the relevant school workflow.

The project-defined identifier length is:

```text
UDISE / UID = 18 digits
PEN         = 11 digits when available
```

The 18-digit definition is a project/workflow fact. Do not claim that the video itself proved the generation rule unless a future recording explicitly demonstrates it.

---

# 135. NA → ND MAPPING

The portal and spreadsheet terminology must remain distinct:

```text
UDISE+ portal:
NA = Not Available

School spreadsheet:
ND = Not Defined
```

The intended mapping is:

```text
Portal NA
   ↓
Spreadsheet ND
```

Do not globally replace the literal strings `NA` and `ND` without understanding which system the value came from.

---

# 136. ND RECONCILIATION IS A SEPARATE OPERATION

The ND check is not merely the final hidden step of New PEN creation.

It is a separate later reconciliation process:

```text
Find students whose PEN = ND
        ↓
Open UDISE+ Student Database
        ↓
Select correct class first
        ↓
Search student name
        ↓
Match correct student
        ↓
Read current PEN
        ↓
Actual PEN available?
       / \
     YES  NO
      ↓    ↓
Update  Keep ND
PEN     
      ↓
Update OGR
      ↓
Log result
```

If no actual PEN is available, retain `ND`.

---

# 137. ND MATCHING SAFETY RULE

The ND process must not blindly accept the first search result.

A candidate should be matched using available identifying information, potentially including:

- student name,
- class,
- DOB,
- gender,
- and other available student identifiers.

The exact final matching hierarchy has not been formally specified.

Therefore:

> If multiple candidates cannot be safely distinguished, stop for manual review rather than silently selecting one.

---

# 138. ACTUAL PEN UPDATE RULE

When the ND reconciliation finds an actual 11-digit PEN:

```text
PEN sheet:
ND → actual PEN

OGR:
ND/blank → actual PEN
```

The dedicated ND recording establishes that the OGR is updated with the actual PEN during reconciliation.

If no actual PEN exists:

```text
PEN sheet = ND
OGR PEN = unchanged pending state
```

No fabricated PEN is permitted.

---

# 139. GOOGLE CLOUD / DESKTOP BOUNDARY

The planned architecture uses the official Google Sheets API for spreadsheet access.

Google Cloud is relevant for:

- Google Sheets API configuration,
- official authorization/credentials setup,
- OAuth/service-account-related configuration as appropriate.

Google Cloud is **not** intended to host the Windows desktop automation application.

The intended application remains a local Windows desktop application.

---

# 140. VISIBLE BROWSER REQUIREMENT

The planned Playwright automation is intended to operate a **visible/headed browser**, not an invisible browser-only process.

Reasons include:

- observing government portal state,
- allowing manual intervention,
- handling unexpected portal behavior,
- controlled consent confirmation,
- debugging,
- screenshots/manual review.

The application should therefore support a controlled visible-browser mode.

---

# 141. CREDENTIAL SECURITY

Government portal credentials must NOT be hardcoded in source code.

Do not hardcode:

- usernames,
- passwords,
- OTPs,
- security answers,
- session tokens,
- Aadhaar values,
- other authentication secrets.

Authentication should be supplied through a secure runtime/configuration mechanism.

The username visible in the recording, `SUNIL PRADHAN`, is an observed example/context value and is not a credential to hardcode.

---

# 142. AADHAAR CONSENT CONTROL

The national portal displayed:

`CONSENT FOR DEMOGRAPHIC AUTHENTICATION`

with:

`I Agree`

Because this represents a legal/consent declaration, the automation should treat it as a controlled manual-intervention point unless the school explicitly authorizes automated confirmation under its established consent procedure.

Do not blindly automate legal consent merely because it is a visible button.

---

# 143. AUTOMATION ARCHITECTURE — CONFIRMED DESIGN DIRECTION

The discussed stack remains:

- **Python** — main application language
- **PySide6** — Windows desktop GUI
- **Playwright** — browser automation
- **Google Sheets API** — spreadsheet read/write
- **SQLite** — local state, checkpoints, logs, retry information
- **PyInstaller** — Windows executable packaging

Conceptual architecture:

```text
Google Sheets
    ↓
Batch Reader / Normalizer
    ↓
Workflow State Engine
    ↓
Class + Entry Condition Router
    ↓
Playwright Visible Browser
    ↓
Government Portal
    ↓
Verified Result
    ↓
Sheet Update
    ↓
SQLite Audit / Retry State
```

---

# 144. STATE-BASED, NOT BLIND CLICK AUTOMATION

The application must be state-driven.

Bad approach:

```text
click
wait 2 seconds
click
wait 2 seconds
click
```

Required approach:

```text
identify current state
      ↓
find correct student
      ↓
verify identity
      ↓
fill required data
      ↓
wait for dependent controls
      ↓
save
      ↓
verify portal result
      ↓
update spreadsheet
```

The application should be able to resume from a known state rather than blindly replaying all previous clicks.

---

# 145. BATCH / SHEET UPDATE MODEL

The intended architecture is:

```text
Read batch
   ↓
Process student
   ↓
Verify result
   ↓
Record local state
   ↓
Update appropriate sheet state
   ↓
Continue next student
```

The application should maintain checkpoints so a failure on one student does not force unnecessary reprocessing of already-completed students.

The exact Google Sheets batch-update implementation can be decided during coding, but the business rule is:

> Never write a completion state before the corresponding portal completion has been verified.

---

# 146. ERROR / MANUAL REVIEW PRINCIPLE

Examples of conditions that should stop automatic completion include:

- student not found,
- multiple ambiguous matches,
- portal validation failure,
- unexpected page/state,
- session expiration,
- required document missing,
- dependent dropdown not loading,
- unexpected portal error,
- import behavior not recognized,
- consent requiring manual confirmation,
- conflicting student identifiers.

In such cases:

```text
DO NOT MARK GREEN
DO NOT FABRICATE DATA
DO NOT GUESS
DO NOT SILENTLY SKIP THE ERROR
```

Instead, log the state and route the student to retry/manual review as appropriate.

---

# 147. DATA PRIVACY / LOGGING PRINCIPLE

The source data can contain sensitive information including:

- Aadhaar,
- mobile numbers,
- dates of birth,
- addresses,
- student identifiers,
- government IDs.

Logs should therefore contain only the information necessary for audit/recovery.

Avoid unnecessarily copying full Aadhaar or other sensitive values into logs/screenshots.

---

# 148. FINAL CLASS ROUTING RULE

The established routing rule remains:

| School class | Route |
|---|---|
| JrKG | Satyam School ID |
| SrKG | Satyam School ID |
| Balvatika | Satyam School ID |
| 1st | Satyam School ID |
| 2nd onward | Block ID |

This applies to both UDISE and PEN workflows.

The exact login implementation for each route remains a live-portal verification/configuration task.

---

# 149. FINAL FOUR-CONDITION MATRIX

```text
                    PEN STATE
                 NEW          IMPORT
              ┌──────────┬──────────────┐
UDISE NEW     │ CONDITION│ CONDITION 2  │
              │    1     │              │
              ├──────────┼──────────────┤
UDISE IMPORT  │ CONDITION│ CONDITION 4  │
              │    3     │              │
              └──────────┴──────────────┘
```

## Condition 1

```text
New UDISE + New PEN
```

Status:

**Fully documented from the analyzed recordings.**

## Condition 2

```text
New UDISE + PEN Import
```

UDISE side:

**Documented.**

PEN import side:

**Pending dedicated import recording.**

## Condition 3

```text
UDISE Import + New PEN
```

New PEN side:

**Documented.**

UDISE import side:

**Pending dedicated import recording.**

## Condition 4

```text
UDISE Import + PEN Import
```

Both import sides:

**Pending dedicated import recordings.**

---

# 150. FINAL SOURCE-DERIVED VS UNRESOLVED BOUNDARY

## Confirmed from the analyzed project material

- Three operational spreadsheets/files.
- OGR staged-entry role.
- UDISE spreadsheet structure.
- PEN spreadsheet structure.
- PEN `IMPORT PENDING` structure.
- PH1/PH2/PH3 operational phases.
- New UDISE workflow.
- CRS-RGI route.
- Manual birth-information route.
- CTS/new-student creation.
- Manage Students profile sections.
- UDISE Personal/Education/Bank/Scholarship & Facility/Health & CWSN structure.
- UDISE full-row green completion rule.
- UDISE-before-PEN dependency for the normal new-entry workflow.
- New PEN initialization.
- Aadhaar verification/consent event.
- General Profile.
- Enrolment Profile.
- Facility Profile.
- Profile Preview.
- `Data completion is complete.`
- Portal `Permanent Education Number - Not Defined`.
- Portal `NA` and spreadsheet `ND` distinction.
- PEN full-row green completion state.
- ND reconciliation.
- Class-first/name-search ND process.
- Actual 11-digit PEN replacement.
- OGR actual-PEN update.
- Class-based Satyam School ID / Block ID routing.
- Four entry conditions.
- State-driven automation architecture.
- Visible browser/manual-intervention direction.
- Credential-security requirements.

## Still unresolved because source material has not yet been supplied/analyzed

- Exact UDISE Import workflow.
- Exact PEN Import workflow.
- Exact Other State PEN Import workflow.
- Exact major-change process.
- Exact import matching rules.
- Exact import status transitions.
- Exact import completion/green-row behavior.
- Exact Condition 4 combined import sequence.
- Final PH processing order/selection algorithm.
- Exact field-by-field mapping for every partially readable portal field.
- Exact portal selectors/DOM attributes.
- Complete exception taxonomy for every live portal error.

These unresolved items are **not to be guessed from general knowledge**.

---

# 151. NEXT-SESSION HANDOFF RULE

A future ChatGPT/coding agent receiving this file must:

1. Treat this document as the authoritative project context.
2. Read the entire document before proposing implementation.
3. NOT ask the user to re-upload the five already-analyzed videos.
4. NOT ask the user to re-explain the New Entry workflow.
5. Preserve the exact project terminology.
6. Preserve the distinction between OGR, UDISE/UID, PEN, ND, NA, IMPORT, and GREEN.
7. Preserve UDISE-before-PEN for the normal New/New branch.
8. Never equate UID presence with complete UDISE processing.
9. Never equate PEN ND with failure.
10. Never turn a row green without verified completion.
11. Skip already-green rows by default.
12. Treat import as a distinct workflow branch.
13. Never invent import steps.
14. Never hardcode credentials or student examples.
15. Keep Aadhaar consent as a controlled/manual point unless explicitly authorized otherwise.
16. Use state-driven rather than coordinate-driven automation.
17. Request/analyze only the missing import recordings when continuing workflow discovery.
18. Do not start final application implementation until the four branches are sufficiently specified.

---

# 152. FINAL CONTEXT SUMMARY

The project is a Windows desktop automation system for structured government student-data workflows.

The central business model is:

```text
STUDENT DATA
    ↓
OGR / UDISE / PEN SHEETS
    ↓
ENTRY CONDITION
    ↓
CLASS + ID ROUTING
    ↓
UDISE NEW OR IMPORT
    ↓
VERIFIED UDISE COMPLETION
    ↓
PEN NEW OR IMPORT
    ↓
VERIFIED PEN COMPLETION
    ↓
SHEET STATE UPDATE
    ↓
LATER ND RECONCILIATION
    ↓
ACTUAL PEN UPDATE WHEN AVAILABLE
```

The key state distinctions are:

```text
NEW
IMPORT
NA
ND
ACTUAL PEN
NOT STARTED
IN-PROGRESS
COMPLETED
GREEN
OGR UNCHANGED COLOR
```

The five previously analyzed recordings are preserved by this master document and do not need to be uploaded again merely for continuity.

The project is **fully documented for the analyzed New Entry and ND workflows** and remains **intentionally open only for the two import workflows**.

---

# END OF FINAL MASTER CONTEXT FILE

# 153. ULTRA CONTEXT CONTINUITY ADDENDUM

## 153.1 Purpose of this addendum

This section exists specifically so that the the current ChatGPT conversation may not be available for use in a later ChatGPT session.

The objective is not merely to preserve the software architecture. The objective is to preserve the operational understanding developed during the conversation so that a future ChatGPT conversation or coding agent can continue the project without requiring the user to explain the already-established workflow again.

This addendum therefore records:

- project purpose;
- exact terminology that must be preserved;
- spreadsheet roles;
- confirmed workflow branches;
- class routing;
- spreadsheet color/state rules;
- UDISE New Entry details;
- PEN New Entry details;
- ND reconciliation details;
- automation architecture;
- safety/security requirements;
- implementation constraints;
- what must never be assumed;
- what remains unresolved;
- recordings already analyzed;
- recordings still required;
- file/context file lineage;
- future-session instructions;
- continuity and backup checklist.

It is intentionally explicit because the source conversation may be unavailable for later continuation.

---

# 154. PROJECT IDENTITY

## 154.1 Project purpose

Build a Windows desktop automation application for repetitive student data entry performed by the school office across:

1. `ONLINE GENERAL REGISTER` (OGR)
2. `UDISE_Entry_(State)`
3. `PEN_Entry_(National)`
4. Gujarat UDISE / Gujarat Child Tracking System portal
5. National UDISE+ / PEN portal

The eventual application should read student information from Google Sheets, normalize and validate it, operate the government portals through a visible/headed browser, verify completion, and update the appropriate spreadsheet rows only after verified completion.

The system is intended to reduce repetitive manual data entry while preserving the existing school workflow and preventing false completion states.

## 154.2 Intended technology direction

Confirmed design direction:

- Operating environment: Windows desktop
- Language: Python
- GUI: PySide6
- Browser automation: Playwright
- Spreadsheet integration: Google Sheets API
- Local database/state: SQLite
- Packaging: PyInstaller
- Browser mode: visible/headed browser
- Google Cloud: used for official Google Sheets API authorization/configuration only
- Government portal credentials: never hardcoded

This is a design direction, not a claim that every dependency or selector has already been finalized.

---

# 155. EXACT PROJECT TERMINOLOGY — DO NOT SILENTLY RENAME

The following terminology was deliberately established and should remain unchanged unless the user explicitly changes it.

## 155.1 OGR

`ONLINE GENERAL REGISTER` is the General Register used by the school.

Do NOT call it the project's "master database" merely for convenience.

It is the school's general register/source record in this workflow.

## 155.2 UID / UDISE

For this project, UID refers to the UDISE identifier generated/used in the school workflow.

The project treats UDISE/UID as an 18-digit value.

Important wording rule:

- describe the 18-digit value as a project-defined operational fact;
- do not claim that the analyzed recordings independently proved a universal UDISE specification unless separately verified.

## 155.3 PEN

PEN means Permanent Education Number.

Project convention:

- actual PEN = 11 digits when available;
- National UDISE+ may show `NA` when PEN is not available after initialization;
- spreadsheet representation of that state is `ND` = Not Defined.

## 155.4 NA → ND

Portal `NA` maps to spreadsheet `ND`.

Do not treat `ND` as an error by default.

## 155.5 GREEN

GREEN means verified completion according to the spreadsheet workflow.

GREEN does not mean:

- the automation merely clicked a button;
- the page loaded;
- a UID exists;
- the student was initialized;
- the process was attempted;
- no visible error appeared.

GREEN must be assigned only after the appropriate completion condition has been verified.

## 155.6 PH1 / PH2 / PH3

PH1, PH2 and PH3 are operational processing batches/phases in the spreadsheet.

They are not different underlying student data structures.

Do not invent special portal logic solely because a student is in PH1, PH2 or PH3 unless future source material establishes it.

---

# 156. THREE OPERATIONAL SPREADSHEET FILES

There are exactly three principal spreadsheet files in the workflow.

## 156.1 ONLINE GENERAL REGISTER

Role:

- general register;
- source/reference student record;
- later receives government identifiers such as UID and PEN;
- its row color is NOT the government completion indicator.

Observed/established fields include:

- AY
- NAME
- STD
- MOBILE 1
- MOBILE 2
- PR
- DOB
- DOA
- DOE
- AADHAR
- UID
- PEN
- T-GR
- TC
- APAAR
- DOCUMENTS PENDING

Example student previously used for workflow understanding:

- AY: 2026-27
- NAME: AISHA BISOYI
- STD: SR KG
- MOBILE 1: 9337302202
- PR: P091
- DOB: 02/01/2022
- DOA: 18/05/2026
- DOE: 23/09/2026
- AADHAR: 617750014825
- UID: 242241000672620025

These values are examples from the analyzed workflow and MUST NOT be hardcoded into the application.

### Critical OGR color rule

OGR row color remains unchanged while UDISE/PEN government processing is completed.

Do not use OGR row color as the UDISE/PEN success flag.

### Critical partial-entry rule

An OGR row can be partially populated or half-filled.

A partially populated OGR row is not proof that government portal entry is complete.

The automation must use the actual government-sheet state and verified portal state, not superficial completeness of the OGR row.

---

# 157. UDISE_Entry_(State) — EXACT STRUCTURE

Tabs:

- PH1
- PH2
- PH3

Exact headers established:

1. REMARK
2. Class
3. UDISE No
4. Birth Cert Reg No
5. Birth Year
6. Birth Month
7. Birth Date
8. Gender
9. Birth State
10. Birth District
11. Birth City
12. Student Name
13. Father's Name
14. Mother's Name
15. Surname
16. Date of Birth
17. GR No
18. Roll No
19. Plot Number
20. Society
21. Landmark
22. Area
23. Pin Code
24. Mother Tongue
25. Date of Join
26. Aadhar Card No
27. Name as per Aadhar
28. Mobile No 1
29. Mobile No 2

PH3 may contain an additional blank/unused column.

### UDISE sheet completion rule

When UDISE processing succeeds and completion is verified:

- the ENTIRE UDISE row becomes GREEN;
- not merely the UDISE/UID cell;
- OGR row color remains unchanged.

### UDISE green gate

A row must not proceed to normal PEN processing merely because a UID/UDISE value appears.

The UDISE completion gate is:

1. required UDISE creation/profile work is complete;
2. relevant required profile sections are complete;
3. portal indicates/permits verified completion;
4. no unresolved required validation remains;
5. the completion result can be safely associated with the correct student.

Only then may the automation mark the UDISE row GREEN and proceed to the next normal stage.

---

# 158. PEN_Entry_(National) — EXACT STRUCTURE

Tabs:

- PH1
- PH2
- PH3
- IMPORT PENDING

Main PH headers:

1. PEN
2. Class
3. Student Father Surname
4. Gender
5. Date of Birth
6. Student State Code (UDISE No)
7. Mother's Name
8. Father's Name
9. Aadhar Number of Student
10. Name of Student as per Aadhar Card
11. Admission Date
12. Full Address
13. Pincode
14. Mobile No 1
15. Mobile No 2
16. Mother Tongue
17. Admission Number in Present School (GR No)
18. Roll No
19. Previous Class Percentage
20. Previous Class Attendance Days
21. Height (cm)
22. Weight (kg)

IMPORT PENDING headers:

1. SR NO
2. STUDENT NAME
3. PEN
4. DOB
5. SCHOOL NAME
6. SCHOOL UDISE
7. STATE
8. DISTRICT
9. BLOCK
10. HEADMASTER
11. CONTACT NO
12. STATUS
13. REMARK

Example import records previously observed include:

- SOUMYA RANJAN BEHERA — PEN 23060444551
- REYANSH SURJYAMANI PATRA — PEN 23428960733

Their examples included source-school/state/district/block/status information.

Do not hardcode these records.

### PEN completion rule

When PEN processing is successfully completed:

- entire PEN row becomes GREEN;
- this remains true even if the final PEN value is `ND`.

Therefore:

`PEN = ND + GREEN` is a valid completed state.

---

# 159. FOUR ENTRY CONDITIONS — MASTER DECISION TABLE

The project has four operational entry conditions.

| Condition | UDISE state | PEN state | Normal interpretation |
|---|---|---|---|
| 1 | New | New | Create UDISE, verify, then create PEN, verify |
| 2 | New | Import | Create UDISE, verify, then process PEN Import workflow |
| 3 | Existing/imported | New | Skip UDISE creation if verified existing/imported state is valid; process New PEN |
| 4 | Existing/imported | Import | Process according to verified existing UDISE + PEN Import workflow |

The exact import behavior is NOT to be invented.

The four-condition structure is confirmed, but the exact source-driven import transitions remain pending until the two remaining recordings are analyzed.

### UDISE before PEN rule

For normal New/New processing:

`UDISE → verified UDISE completion → PEN`

Do not reverse this order.

### Already-GREEN rule

Already GREEN rows are considered completed and should be skipped by default.

They should not be reprocessed merely because they are present in the sheet.

A deliberate manual re-check may exist as a separate operation.

---

# 160. CLASS ROUTING — CONFIRMED

The class routing rule applies to both UDISE and PEN workflows.

## 160.1 Satyam School ID workflow

Classes:

- JrKG
- SrKG
- Balvatika
- 1st

Use the Satyam School ID workflow.

## 160.2 Block ID workflow

Classes:

- 2nd onward

Use the Block ID workflow.

The exact login implementation should not be hardcoded until live portal behavior is verified.

Do not replace this routing with an inferred generic login scheme.

---

# 161. RECORDINGS ALREADY ANALYZED

The following five recordings were already analyzed in the source conversation.

They do NOT need to be uploaded again merely to restore the already-understood parts of the project.

## 161.1 GOOGLE SHEET.mp4

Approximate duration: 1:55.

Purpose/confirmed content:

- demonstrates the spreadsheet-side workflow;
- confirms the three working sheets/files;
- shows OGR staging/basic entry;
- establishes that spreadsheet state is central to the workflow.

## 161.2 GUJARAT ENTRY.mp4

Approximate duration: 10:44.

Purpose/confirmed content:

- detailed Gujarat UDISE New Entry workflow;
- birth-data entry;
- CTS student creation;
- Manage Students;
- Personal profile;
- Education profile;
- Bank profile;
- Scholarship & Facility;
- Health & CWSN;
- final Save Student;
- completion expectations.

## 161.3 AFTER UDISE ENTRY BEFORE PEN.mp4

Approximate duration: 2:03.

Purpose/confirmed content:

- post-UDISE state;
- UID/UDISE populated;
- PEN remains separate/pending according to the entry condition;
- OGR color remains unchanged;
- establishes the UDISE→PEN transition.

## 161.4 PEN ENTRY.mp4

Approximate duration: 6:15.

Purpose/confirmed content:

- detailed National UDISE+ New PEN workflow;
- initialization;
- success modal;
- General Profile;
- Enrolment Profile;
- Facility Profile;
- Profile Preview;
- completion modal;
- spreadsheet update;
- PEN=ND is a successful possible final state.

## 161.5 5 ND MANUAL UPDATE.mp4

Approximate duration: 1:52.

Purpose/confirmed content:

- later ND reconciliation;
- open National UDISE+ Student Database;
- select class first;
- search student by name;
- match correct student;
- read current PEN;
- update PEN sheet and OGR if an actual PEN exists;
- retain ND if no actual PEN exists.

---

# 163. GUJARAT UDISE NEW ENTRY — FULL CONFIRMED WORKFLOW

## 163.1 Portal context

Observed portal/workflow:

- Gujarat Child Tracking System / Gujarat UDISE
- school: SATYAM STARS INTERNATIONAL SCHOOL

Observed left navigation included:

- Home
- Manage Students
- Student Tracking Report
- Student Transfer Request List
- GSRSE Voucher
- Back To School Phase2
- Attendance Report
- Student Identity (SID) Number Entry
- Early Warning System
- Add Local Holiday
- and other portal navigation items.

## 163.2 Student New Entry

New Student Entry provides birth-data routes.

### Route A — CRS-RGI

Observed fields/controls:

- BRN
- Birth Year
- Birth Month
- Birth Date
- Gender
- `GET DETAILS FROM CRS-RGI`

### Route B — Manual

Observed fields include:

- Birth State
- Birth District
- Birth Taluka
- Birth City/Place
- Birth Village
- Year
- Month
- Date
- BRN
- Birth Certificate No.
- PDF upload
- Next

Example observed manual birth data:

- State: Odisha
- District: Ganjam
- Taluka: Sheragada
- Date: 02 January 2022
- BRN: 13/2022
- birth certificate PDF uploaded

These are examples, not fixed application values.

## 163.3 Gender

Observed options:

- Male
- Female
- Other

## 163.4 CTS new student fields

Observed:

- Student name
- Father name
- Mother name
- Surname
- DOB
- Disabled yes/no
- Disability type
- `ADD NEW STUDENT`

## 163.5 Manage Students

Observed list columns included:

- Aadhaar/UID
- Student Name
- Father Name
- Mother Name
- Surname
- DOB
- DOA
- GR No
- Section
- Status
- Edit

## 163.6 Student profile tabs

Observed tabs:

1. Personal
2. Education
3. Bank
4. Scholarship & Facility
5. Health & CWSN

## 163.7 Personal example

Previously observed Aisha values:

- Student: AISHA
- Father: TOFAN
- Mother: PRIYANKA
- Surname: BISOYI
- Guardian: TOFAN BISOYI
- Area/locality: PANDESARA
- District/city codes as observed: 2422-SURAT / SURAT CORPO.
- Address/locality: SHREE RAMNAGAR
- Road: BAMROLI ROAD
- PIN: 394221
- Mother tongue: 12-Odia
- DOB: 02/01/2022
- Gender: 2-Girl
- Category: 1-General
- Religion: 11-General

Bottom buttons:

- SAVE STUDENT
- CLEAR

## 163.8 Education

Observed fields around the education section included approximately fields 28–41:

- admission number;
- admission date;
- class;
- RTE;
- previous academic status/result;
- percentage;
- attendance;
- medium/language;
- subjects.

Example:

- PR: P091
- roll/admission: 91
- date: 18/05/2026
- class: 102-Sr.KG
- medium: English

Class dropdown observed:

- PP-3
- PP-2
- PP-1
- I
- II
- III
- IV
- V
- VI
- VII
- VIII
- IX
- X
- XI
- XII

Education also includes language/subject selection involving:

- mandatory/general;
- additional;
- co-curricular.

## 163.9 Bank

Bank fields observed around 42–46.

Values may legitimately be:

- NA;
- blank;
- not applicable.

Do not manufacture bank information merely to satisfy a field.

## 163.10 Scholarship & Facility

This profile section exists.

The exact field-by-field mapping was not sufficiently readable/confirmed in the source material.

Therefore:

- the section is known;
- its exact automation mapping remains a live-DOM verification task;
- do not invent exact field numbers or option mappings.

## 163.11 Health & CWSN

Observed fields around 62–81 included concepts such as:

- CWSN status;
- disability/impairment;
- UID/UDID;
- learning disability;
- dysgraphia;
- dyscalculia;
- dyslexia;
- ASD;
- ADHD;
- intellectual/developmental disability;
- folic/iron facilities;
- vitamin A facilities;
- related health/CWSN fields.

Exact numbering and final field mapping require live DOM verification.

## 163.12 Final UDISE save

Final control:

`SAVE STUDENT`

Successful completion means the relevant UDISE profile is actually complete, not merely that this button was clicked.

---

# 164. NATIONAL UDISE+ / PEN NEW ENTRY — FULL CONFIRMED WORKFLOW

## 164.1 Portal context

Observed URL pattern:

`sdms.udiseplus.gov.in/g2/#/school/...`

The application should use the currently configured portal URL rather than blindly hardcoding an observed path.

Observed school context:

- UDISE code: 24224100067
- Category: 1 Primary
- Type: 3 Co-educational
- Management: 5 Pvt. Unaided (Recognized)
- Class: Nursery/KG/PP3-5
- School: SATYAM STARS INTERNATIONAL SCHOOL
- AY: 2026-27

Observed user label:

- SUNIL PRADHAN

Do not hardcode credentials.

## 164.2 Example new student

AISHA TOFAN BISOYI

Observed class representation:

- LKG/KG1/PP2

Section:

- A

DOB:

- 02/01/2022

## 164.3 Initialization success modal

Observed success wording/concept:

`The Student has been initialised/Saved Successfully.`

It showed:

- Student Name
- Class

Buttons:

- Add New Student
- Go to New Entry List
- Fill General Profile

This is initialization success, not by itself proof that the entire PEN profile is complete.

## 164.4 PEN workflow stages

Confirmed stage sequence:

1. General Profile
2. Enrolment Profile
3. Facility Profile
4. Profile Preview

## 164.5 Header state

Observed:

- Permanent Education Number - Not Defined
- Student AADHAAR Verified
- CWSN No
- Impairment Type NA

## 164.6 General Profile

Observed/confirmed data concepts:

- guardian name;
- Aadhaar;
- name as per Aadhaar;
- admission date;
- primary mobile;
- alternate mobile;
- CWSN;
- address;
- pincode;
- email;
- mother tongue;
- social category;
- religion;
- BPL;
- AAY;
- EWS/disadvantaged;
- CWSN.

### Aadhaar consent

Observed dialog:

`CONSENT FOR DEMOGRAPHIC AUTHENTICATION`

with:

`I Agree`

Automation must treat this as a controlled/manual consent step unless the school's lawful consent process explicitly authorizes automated handling.

Do not silently automate consent simply because Playwright can click it.

## 164.7 Example address/data

Observed example:

`183, SHREE RAMNAGAR, BAMROLI ROAD, PANDESARA, Surat, Gujarat, 394221`

PIN:

`394221`

Mobile:

`9337302202`

Mother tongue:

`114-ODIA - Odia`

Category:

`1-GENERAL`

Religion options observed included:

- Muslim
- Christian
- Sikh
- Buddhist
- Parsi
- Jain
- NA

These are examples/observed option sets, not values to force for every student.

## 164.8 Enrolment Profile

Observed concepts:

- Admission number, e.g. P089
- Admission date, e.g. 18/05/2026
- class/roll
- medium, e.g. 19-English
- language group, e.g. English
- foreign language area
- mandatory/general subjects
- additional subjects
- co-curricular subjects
- previous academic status, e.g. `1-Studied at Current/Same School`
- previous class
- RTE 12C yes/no
- RTE amount
- previous result
- previous class percentage
- attendance days

## 164.9 Facility Profile

Observed concepts:

- competitions/olympiads yes/no
- NCC/NSS/Scouts & Guides
- height, e.g. 105 cm
- weight, e.g. 45 kg
- distance to school, e.g. `1-Less than 1 km`
- highest education level of mother
- highest education level of father
- highest education level of legal guardian
- Save/Next
- validation behavior

Again, example values are not defaults.

## 164.10 Final completion

Observed final modal:

`Data completion is complete.`

Buttons included:

- Okay
- Back to Student Dashboard

This is the relevant completion evidence for the New PEN workflow.

## 164.11 Spreadsheet result

After successful New PEN completion:

- PEN sheet value is set to `ND` when the portal has not defined an actual PEN;
- entire PEN row becomes GREEN;
- OGR color remains unchanged.

---

# 165. ND RECONCILIATION — FULL CONFIRMED WORKFLOW

ND reconciliation is separate from the normal New PEN workflow.

It should not automatically be treated as the immediate next click after every New PEN completion.

## 165.1 Purpose

Find whether a student whose spreadsheet PEN is `ND` has subsequently received an actual 11-digit PEN in National UDISE+.

## 165.2 Steps

1. Open National UDISE+ Student Database.
2. Select the correct class first.
3. Search for the student by name.
4. Match the correct student.
5. Read the current PEN.
6. If an actual 11-digit PEN exists:
   - replace `ND` in PEN sheet;
   - update PEN in OGR.
7. If no actual PEN exists:
   - keep `ND`.

## 165.3 Matching safety

If multiple students are returned and the correct student cannot be distinguished safely, do not silently choose the first result.

Mark for manual review.

Possible matching evidence can include available identifiers such as:

- name;
- DOB;
- class;
- gender;
- school context;
- other available student information.

Do not use an unverified fuzzy match as proof.

## 165.4 Example actual PENs observed

Examples included:

- 23613114903
- 23584566926

These are examples from the analyzed workflow, not application constants.

---

# 166. DATA NORMALIZATION REQUIREMENTS

Before portal automation, the application should create a normalized student object rather than passing raw spreadsheet cells directly to Playwright.

Normalization areas:

- names;
- father name;
- mother name;
- surname;
- gender;
- class;
- dates;
- mobile numbers;
- Aadhaar values;
- UID/UDISE;
- PEN;
- missing values;
- NA/ND;
- address components;
- roll/admission number;
- mother tongue;
- categorical portal values.

## 166.1 Dates

Internally use date objects or a normalized date representation.

Do not trust Google Sheets display formatting.

Convert to the portal's expected format only at the portal boundary.

The project previously encountered date-format issues where Canva/other tools converted dd/mm/yyyy-like values into other representations. Therefore, date formatting must be explicitly controlled.

## 166.2 Class normalization

Potential spreadsheet/user labels include:

- JR KG
- Sr KG
- SR.KG
- Balvatika
- 1st
- 2nd
- LKG/KG1/PP2
- UKG/KG2/PP1
- portal-coded values such as 102-Sr.KG

Create a mapping layer rather than scattering string comparisons throughout the code.

---

# 167. FIELD MAPPING LAYER

Required architecture:

`source sheet → normalized student object → portal field mapping`

Do not directly bind spreadsheet column numbers to portal selectors throughout the automation.

This allows:

- spreadsheet header changes to be isolated;
- portal selector changes to be isolated;
- different UDISE/PEN workflows to reuse normalized data;
- validation before browser interaction.

The mapping layer should distinguish:

- source value;
- normalized value;
- target portal field;
- transformation;
- validation rule;
- required/optional status;
- unresolved/manual status.

---

# 168. PORTAL SELECTOR STRATEGY

Selector priority:

1. stable element ID;
2. name attribute;
3. data-* attribute;
4. accessible label;
5. associated label;
6. stable text;
7. table row + column relation;
8. CSS/XPath only when necessary.

Do not base production automation on fragile coordinates or blind mouse clicks.

Live DOM inspection is required before final selector implementation.

---

# 169. DROPDOWN AND DEPENDENCY STRATEGY

For every dropdown:

1. identify it by label/context;
2. inspect available options;
3. select the exact intended option;
4. wait for dependent data to load;
5. verify the selected option;
6. continue only when the page state is stable.

Dependent examples:

- State → District
- District → Taluka
- Taluka → City/Village
- Class → subject options
- CWSN Yes → disability options
- category → related fields

Do not assume a dependent dropdown is populated immediately after changing its parent.

---

# 170. FILE UPLOAD REQUIREMENT

Birth certificate PDF upload is part of the manual UDISE birth-entry route.

The application should support file upload when the workflow is automated.

However, the exact portal file-size/type constraints were not fully confirmed from the source material.

Therefore:

- inspect live DOM/validation;
- do not hardcode an invented maximum file size;
- preserve the original PDF file path/reference where appropriate;
- log upload failures clearly.

---

# 171. STATE-DRIVEN AUTOMATION MODEL

The automation must be state-driven, not a blind click macro.

Suggested state sequence:

```text
READ_SHEETS
    ↓
VALIDATE_STUDENT
    ↓
SKIP_IF_ALREADY_GREEN
    ↓
DETERMINE_CLASS_ROUTE
    ↓
DETERMINE_ENTRY_CONDITION
    ↓
RUN_UDISE_BRANCH
    ↓
VERIFY_UDISE
    ↓
RUN_PEN_BRANCH
    ↓
VERIFY_PEN
    ↓
UPDATE_SHEETS
    ↓
LOG_SUCCESS
```

Separate later operation:

```text
CHECK_ND_PEN
    ↓
MATCH_STUDENT
    ↓
READ_CURRENT_PEN
    ↓
UPDATE_IF_ACTUAL_PEN_EXISTS
```

---

# 172. AUTOMATION FAILURE PRINCIPLES

The application must never mark a row GREEN when:

- portal rejected the student;
- import did not match;
- required field failed validation;
- session expired before completion;
- portal timed out before completion was verified;
- wrong student may have been selected;
- a dependent dropdown was not populated correctly;
- the browser crashed before confirmation;
- only the initial profile was created but later required sections remain incomplete;
- only UID appeared but full UDISE completion was not verified;
- PEN initialization occurred but final PEN profile completion was not verified;
- an import workflow was merely attempted;
- the automation cannot distinguish success from failure.

Correct result in these cases:

- retain non-GREEN state;
- log the failure;
- capture screenshot where useful;
- preserve retry state;
- optionally mark for manual review.

---

# 173. SESSION MANAGEMENT

Government portals may:

- timeout;
- logout;
- require reauthentication;
- display unexpected modal dialogs;
- return unauthorized/session errors.

The application should detect these states rather than treating the resulting page as a successful submission.

Credentials must never be stored in source code.

Potential future design:

- secure credential entry;
- environment/configuration mechanism;
- session reuse only where permitted;
- manual login option;
- visible browser for intervention.

Exact credential-storage implementation is not yet fixed.

---

# 174. BATCH PROCESSING AND CHECKPOINTS

The application should process students in batches rather than assuming an uninterrupted run.

A checkpoint should preserve at least:

- student identifier/reference;
- name;
- class;
- PH batch;
- entry condition;
- current UDISE state;
- current PEN state;
- portal status;
- sheet-update state;
- error state;
- retry count;
- timestamp;
- screenshot path when applicable.

If the application closes or the browser fails, it should resume from a known state instead of blindly repeating all students.

---

# 175. LOCAL LOGGING

SQLite is intended to maintain durable local state/logging.

Suggested fields:

- timestamp;
- student identifier;
- student name;
- class;
- PH;
- entry condition;
- UDISE result;
- PEN result;
- portal status;
- sheet update status;
- error code/message;
- retry count;
- screenshot path;
- manual-review flag.

Minimize sensitive data in logs.

Do not unnecessarily duplicate full Aadhaar numbers or other sensitive information into logs.

---

# 176. MANUAL INTERVENTION CONTROLS

The eventual desktop GUI should support operational controls such as:

- Start
- Pause
- Resume
- Retry
- Skip
- Open Student
- Mark for Manual Review
- Re-check
- Check ND Students
- View Logs

These are design directions and should be implemented only after the underlying workflow is stable.

---

# 177. GOOGLE CLOUD BOUNDARY

Google Cloud is not the hosting environment for the desktop automation application.

Its role is limited to official Google Sheets API configuration/authorization as required.

The desktop application itself runs locally on Windows.

The intended high-level architecture is:

```text
Google Sheets
     ↓
Python desktop application
     ↓
Normalization / validation / state engine
     ↓
Playwright visible browser
     ↓
Government portals
     ↓
Verified result
     ↓
Google Sheets update
     ↓
SQLite local state/logs
```

---

# 178. SECURITY / CREDENTIAL RULES

Never hardcode:

- government portal usernames;
- government portal passwords;
- Google API secrets;
- service-account private keys;
- personal student credentials/data as source-code constants.

The application should obtain configuration through a secure, controlled mechanism.

The example student data in this context file is workflow documentation, not permission to embed those values in code.

---

# 179. AADHAAR / CONSENT CONTROL

Aadhaar-related authentication is sensitive.

The observed National UDISE+ flow included a demographic-authentication consent dialog.

The automation must not assume that a programmatic click on `I Agree` is automatically authorized.

The project rule is:

- keep the consent step controlled/manual unless the school's lawful consent process explicitly authorizes automation;
- document any future authorization before changing this rule.

---

# 180. IMPORTANT DISTINCTION — INITIALIZATION VS COMPLETION

This distinction is fundamental.

## UDISE

Creating/initializing the student is not necessarily equivalent to completing the student's full UDISE profile.

## PEN

Initializing a new profile and receiving the initialization-success modal is not necessarily equivalent to completing General + Enrolment + Facility + Preview.

## Spreadsheet

Seeing a UID/PEN value is not necessarily equivalent to the corresponding government workflow being fully completed.

## GREEN

GREEN is a verified completion state.

---

# 181. IMPORTANT DISTINCTION — PEN ND VS PEN FAILURE

`ND` means the school spreadsheet currently does not have a defined/actual PEN for the student.

In the observed New PEN workflow, the portal can successfully complete profile data while the PEN remains not defined.

Therefore:

```text
PEN = ND
AND
PEN ROW = GREEN
```

is valid.

This state should not be retried as if the PEN entry failed.

Later ND reconciliation is the mechanism for checking whether an actual PEN becomes available.

---

# 182. IMPORTANT DISTINCTION — OGR COLOR VS GOVERNMENT SHEET COLOR

Do not confuse:

- OGR row color;
- UDISE sheet row color;
- PEN sheet row color;
- portal status.

The confirmed rules are:

| Object | Completion color behavior |
|---|---|
| OGR | unchanged during government completion |
| UDISE sheet | entire row GREEN after verified UDISE completion |
| PEN sheet | entire row GREEN after verified PEN completion, including ND |
| Portal | has its own status indicators/modal states |

---

# 183. PORTAL STATUS VS SPREADSHEET STATUS

National UDISE+ portal status indicators can include states such as:

- Not Started
- In-Progress
- Completed

Profile indicators include:

- GP
- EP
- FP

These portal statuses must not be mechanically equated with spreadsheet GREEN without checking the workflow's actual completion rule.

The observed final PEN workflow maps verified profile completion to a GREEN spreadsheet row.

---

# 184. IMPORT WORKFLOW — STRICT UNKNOWN BOUNDARY

The following must remain explicitly unresolved until the UDISE Import and PEN Import/Other State recordings are analyzed.

## UDISE Import unknowns

- exact screen navigation;
- exact import controls;
- matching criteria;
- whether import creates, links, or updates records;
- status transitions;
- exact required fields;
- whether manual verification is required;
- success modal/status;
- spreadsheet GREEN rule;
- error handling;
- duplicate behavior.

## PEN Import / Other State unknowns

- exact navigation;
- source-school selection;
- Other State handling;
- exact matching criteria;
- whether existing PEN is linked/imported;
- import status values;
- completion confirmation;
- GREEN behavior;
- interaction with IMPORT PENDING sheet;
- exact OGR update behavior;
- duplicate handling;
- rejection handling.

Do not fill these gaps with assumptions.

---

# 185. IMPORT PENDING SHEET — KNOWN ROLE

The `IMPORT PENDING` tab exists in the PEN workbook.

Known columns:

- SR NO
- STUDENT NAME
- PEN
- DOB
- SCHOOL NAME
- SCHOOL UDISE
- STATE
- DISTRICT
- BLOCK
- HEADMASTER
- CONTACT NO
- STATUS
- REMARK

The tab is clearly associated with import-related work.

However, the exact operational transitions between:

- IMPORT PENDING;
- portal import action;
- successful import;
- PH sheet;
- GREEN;
- OGR PEN;

remain source-dependent and unresolved until the import recordings are analyzed.

---

# 186. EXAMPLE DATA MUST NEVER BECOME CODE CONSTANTS

The following are documentation examples only:

- AISHA BISOYI
- AISHA TOFAN BISOYI
- 9337302202
- 617750014825
- 242241000672620025
- P091
- 18/05/2026
- 02/01/2022
- 394221
- 24224100067
- 23613114903
- 23584566926
- 23060444551
- 23428960733

They exist to explain the workflow.

The application must read actual values from the current spreadsheets.

---

# 187. FUTURE IMPLEMENTATION ORDER

When the missing import recordings are supplied/analyzed, implementation should proceed in this order:

1. Freeze the source-derived workflow specification.
2. Analyze UDISE Import.
3. Analyze PEN Import / Other State.
4. Update the four-condition matrix.
5. Resolve import status transitions.
6. Resolve import GREEN rules.
7. Resolve Condition 4 exact sequence.
8. Verify exact field mappings.
9. Inspect live DOM/selectors.
10. Build normalized data model.
11. Build Google Sheets read/write layer.
12. Build SQLite state/logging layer.
13. Build browser/session manager.
14. Build UDISE New branch.
15. Build UDISE Import branch.
16. Build PEN New branch.
17. Build PEN Import/Other State branch.
18. Build ND reconciliation branch.
19. Build verification gates.
20. Build GUI controls.
21. Test on a small controlled batch.
22. Test failure/retry/resume.
23. Test duplicate/already-GREEN behavior.
24. Test manual intervention.
25. Package with PyInstaller.
26. Only then scale to normal school batch processing.

---

# 188. FUTURE CHATGPT / CODING AGENT INSTRUCTIONS

A future assistant receiving only this file should follow these rules.

## Rule 1 — Treat this context file as the current project source of truth

Do not ask the user to repeat the five already analyzed workflows unless a specific missing detail is required.

## Rule 2 — Preserve terminology

Use:

- OGR
- UDISE/UID
- PEN
- NA
- ND
- PH1/PH2/PH3
- IMPORT PENDING
- GREEN

with the meanings defined here.

## Rule 3 — Do not invent import logic

The two missing recordings are the only major workflow evidence still required.

## Rule 4 — Preserve New Entry

The existing New Entry workflow must remain unchanged when import workflows are added.

Only the import-specific branch should be added/changed.

## Rule 5 — Preserve ND semantics

PEN=ND can be a valid successful completed state.

## Rule 6 — Preserve color semantics

OGR color remains unchanged.

UDISE/PEN sheet rows become GREEN only after verified completion.

## Rule 7 — Verify before writing GREEN

A click is not a completion signal.

## Rule 8 — Skip existing GREEN rows by default

Do not unnecessarily reprocess completed rows.

## Rule 9 — UDISE gate before normal PEN

For normal new processing, verified UDISE completion must precede PEN.

## Rule 10 — Keep consent controlled

Do not silently automate Aadhaar demographic-authentication consent.

## Rule 11 — Credentials are configuration, never source code

## Rule 12 — Use a visible/headed browser

This supports observation, debugging, and manual intervention.

## Rule 13 — Use state-driven automation

Do not build a coordinate-based click macro.

## Rule 14 — Use live DOM verification before final selectors

The context filed observations do not constitute a permanent selector specification.

## Rule 15 — Keep source facts separate from assumptions

If the context file says unresolved, keep it unresolved until new evidence is supplied.

---

# 189. CONTEXT FILE HISTORY

Previous master:

`Satyam_Government_Student_Entry_Automation_MASTER_EXPERT_v2.md`

Final context file before this addendum:

the earlier v3 master

This ultra context file:

the earlier v4 master

The v4 file preserves the v3 context file and appends this continuity/next-session-safety addendum.

Therefore the v4 file should be treated as the preferred context file for starting a later session.

---

# 190. WHAT THIS CONTEXT FILE DOES NOT CLAIM

This context file does NOT claim that:

- every portal field has already been mapped to a stable selector;
- every import workflow has been analyzed;
- every portal error message has been catalogued;
- every live portal behavior is permanent;
- every example value is a default;
- government portal specifications have been independently researched;
- the application is already implemented;
- a production-safe automation can be deployed without live testing;
- Aadhaar consent may be automatically accepted;
- import matching can be safely guessed.

Those distinctions are intentional.

---

# 191. SOURCE-DERIVED FACT VS IMPLEMENTATION INFERENCE

## Source-derived / confirmed in project material

- three principal spreadsheets;
- OGR role;
- UDISE workbook tabs and headers;
- PEN workbook tabs and headers;
- four entry conditions;
- class routing;
- UDISE New Entry workflow;
- PEN New Entry workflow;
- ND reconciliation workflow;
- UDISE full-row GREEN rule;
- PEN full-row GREEN rule;
- PEN ND + GREEN valid state;
- OGR color unchanged;
- five analyzed recordings;
- two missing import recordings;
- visible/headed browser direction;
- credentials not hardcoded;
- Google Cloud limited to Google Sheets API configuration/authentication;
- state-driven architecture direction.

## Implementation inference / engineering design

- Python;
- PySide6;
- Playwright;
- Google Sheets API;
- SQLite;
- PyInstaller;
- selector priority;
- checkpoint model;
- detailed logging schema;
- proposed GUI controls;
- normalization architecture;
- retry/resume architecture.

These are engineering choices and can be refined without changing the source workflow.

---

# 192. FINAL NEXT-SESSION CONTINUITY CHECKLIST

Before deleting the conversation, the user should:

- [ ] Download the earlier v4 master.
- [ ] Open the downloaded Markdown file.
- [ ] Confirm the file contains sections 1–192.
- [ ] Confirm the five analyzed recordings are listed.
- [ ] Confirm the two pending recordings are listed.
- [ ] Confirm the four-condition matrix is present.
- [ ] Confirm UDISE and PEN sheet headers are present.
- [ ] Confirm class routing is present.
- [ ] Confirm ND reconciliation is present.
- [ ] Confirm GREEN rules are present.
- [ ] Confirm OGR color rule is present.
- [ ] Confirm import workflow is explicitly marked unresolved rather than guessed.
- [ ] Keep a second backup copy outside ChatGPT if the project is important.
- [ ] Only after verifying the file, delete/context file the current conversation if desired.

---

# 193. FAST RESTORATION IN A NEW CHAT

If this conversation is deleted, start the next conversation by uploading this file and saying:

> This is the master context file for my Satyam Government Student Entry Automation project. Read it fully and treat it as the current project source of truth. Do not make me repeat the already documented workflow. Preserve all terminology and rules. The only major workflow recordings still missing are UDISE Import and PEN Import / Other State. Do not invent those workflows. Continue from the context file.

If the two missing recordings are later supplied, the next assistant should:

1. read this context file;
2. analyze the new recording(s);
3. append/replace only the unresolved import sections;
4. preserve all confirmed New Entry and ND workflows;
5. update the four-condition matrix;
6. explicitly document any newly discovered differences;
7. not silently rewrite confirmed rules.

---

# 194. FINAL PROJECT STATE AT CONTEXT-FILE GENERATION

## Confirmed

The project has a detailed source-derived understanding of:

- spreadsheet staging;
- OGR role;
- UDISE New Entry;
- post-UDISE state;
- PEN New Entry;
- PEN=ND successful state;
- ND reconciliation;
- class routing;
- four entry conditions at the decision level;
- spreadsheet color semantics;
- automation architecture;
- security constraints;
- visible-browser requirement;
- Google Sheets integration direction;
- local logging/state direction.

## Pending

The remaining evidence gap is primarily the import side:

- UDISE Import;
- PEN Import / Other State;
- exact import matching;
- exact import status transitions;
- exact import completion criteria;
- exact import GREEN behavior;
- exact Condition 4 sequence;
- import-specific exception handling.

## Non-negotiable principle

Do not sacrifice source accuracy for the appearance of completeness.

An explicit `UNRESOLVED` entry is preferable to a fabricated workflow.

---

# 195. FINAL CONTEXT FILE STATEMENT

This file is intended to be sufficient as the durable project handoff for later continuation of the current ChatGPT conversation.

It preserves the previously created final master context file and adds a next-session-safe continuity layer so that the project can be restored from the Markdown file alone, subject to the explicitly documented unresolved import workflows and any future changes in the live government portals.

The user should treat this v4 file as the preferred context file copy.

# END OF ULTRA-DETAILED MASTER CONTEXT FILE


---

# 196. CRYSTAL-CLEAR WORKFLOW DOCUMENTATION STANDARD — REQUIRED FOR ALL FUTURE VIDEO-DERIVED SECTIONS

The previous context file contained correct business rules but some workflow sections were too compressed. From this version onward, every video-derived workflow must be documented so that a developer can implement automation without reopening the source recording for ordinary understanding.

For every meaningful interaction, document the following sequence whenever the source supports it:

1. **Starting screen/state** — what page, sheet, tab, row, modal, or portal state is visible.
2. **User action** — what the user clicked, selected, typed, uploaded, or changed.
3. **Visible control** — exact button/field/tab/dropdown text when readable.
4. **Immediate UI response** — popup, page change, validation, loading state, changed field, table refresh, etc.
5. **Data consequence** — which student value changed and where.
6. **Verification** — how the user knew the action succeeded.
7. **Spreadsheet consequence** — exact sheet/cell/row/color/status change.
8. **Automation rule** — what the program should reproduce.
9. **Failure/problem observed** — error, delay, ambiguity, validation, wrong selection, or other issue.
10. **Recovery action** — what the user did to recover, if observed.
11. **State after recovery** — what the record looked like after recovery.
12. **Source boundary** — explicitly say when the recording does not establish a detail.

Never collapse a sequence such as:

`click save → success → update sheet`

into a single sentence when the underlying recording establishes more detail. Instead use:

```text
ACTION
  ↓
PORTAL RESPONSE
  ↓
VERIFICATION
  ↓
DATA STATE CHANGE
  ↓
SHEET STATE CHANGE
  ↓
NEXT DECISION
```

This is the required documentation format for the remaining UDISE Import and PEN Import / Other State recordings as well.

---

# 197. AUTOMATION DESIGN PRINCIPLE — DOCUMENT THE STATE, NOT JUST THE CLICKS

A reliable automation is not a blind replay of mouse clicks. Every recorded click must ultimately be translated into a state transition.

For each workflow step, the final master documentation should answer:

```text
PRECONDITION
    ↓
ACTION
    ↓
EXPECTED UI RESPONSE
    ↓
EXPECTED DATA RESPONSE
    ↓
VERIFICATION
    ↓
PERSISTED STATE
    ↓
NEXT ACTION
```

If an expected response does not occur, the automation must not continue simply because the button was clicked.

This is mandatory for UDISE, PEN, imports, ND reconciliation, spreadsheet updates, and every future portal workflow.

---

# 198. CRYSTAL-CLEAR RULE FOR VIDEO ANALYSIS — DO NOT LOSE OBSERVED PROBLEMS

For every future recording, any problem encountered by the user must be preserved even if the user successfully worked around it.

Examples of information that must be recorded when observed:

- page loading delay,
- validation error,
- dropdown not immediately populated,
- dependent dropdown delay,
- incorrect first search result,
- duplicate student names,
- modal appearing after save,
- save button requiring another click,
- portal session timeout,
- unexpected `NA`/`ND`,
- spreadsheet color not changing automatically,
- import row not matching,
- status changing from one state to another,
- any manual intervention.

The automation specification must explain not only the happy path but also the observed recovery path.

---

# 199. IMPORTANT LIMITATION OF THIS VERSION

This v5 context file improves the descriptive reconstruction of the AFTER-UDISE handoff and establishes the required documentation standard. It does **not** fabricate exact clicks that are not preserved in the surviving source analysis.

The exact unresolved source workflows remain:

- UDISE Import
- PEN Import / Other State
- major-change import behavior
- import matching rules
- import status transitions
- import completion/green behavior

When those recordings are analyzed, their sections must be written using the crystal-clear standard in Sections 196–198.

The five previously analyzed recordings remain part of the project history and should not be unnecessarily re-requested merely because this section was rewritten.

---

# 200. FINAL CRYSTAL-CLEAR COVERAGE AUDIT — PURPOSE

This section is the final audit layer for this context file.

The purpose is not to add new workflow facts. The purpose is to make the context file usable by a developer, automation engineer, QA person, or future ChatGPT session **without requiring the original conversation history or re-watching the already-analyzed videos**.

A workflow description is considered sufficiently documented only when a reader can answer all of the following for the relevant state:

1. What is the starting state?
2. Which student is being processed?
3. Which spreadsheet is the source?
4. Which sheet/tab contains the record?
5. Which portal is being used?
6. Which class-based login/routing rule applies?
7. What action is performed first?
8. What does the user click/select/type/upload?
9. What does the portal display immediately afterward?
10. Which data fields change?
11. Which data fields remain unchanged?
12. What confirms success?
13. What indicates failure or an unexpected state?
14. What spreadsheet status/color should result?
15. What is the next state?
16. What should happen if the browser/session fails?
17. What should happen if the portal response is ambiguous?
18. What should happen if multiple students match?
19. Can the process safely resume after interruption?
20. Is the behavior confirmed from source material or still unresolved?

No implementation should silently fill a missing answer from guesswork.

---

# 201. MASTER WORKFLOW MAP — HUMAN PROCESS AND AUTOMATION PROCESS

## 201.1 End-to-end business workflow

```text
STUDENT ADMISSION
        ↓
DOCUMENTS COLLECTED
        ↓
DOCUMENT COMPLETENESS VERIFIED
        ↓
STUDENT DATA DIGITIZED
        ↓
PHASE ASSIGNED (PH1 / PH2 / PH3)
        ↓
SCHOOL IMPORT EXCEL PREPARED
        ↓
EXCEL IMPORTED INTO SCHOOL WEBSITE
        ↓
WEBSITE REPORT SECTION
        ↓
READY STUDENTS SELECTED
        ↓
UDISE / STATE EXCEL GENERATED
        ↓
PEN / NATIONAL EXCEL GENERATED
        ↓
GOVERNMENT ENTRY AUTOMATION
        ↓
CLASS ROUTING
        ↓
ENTRY CONDITION DETECTION
        ├───────────────┐
        ↓               ↓
     UDISE            PEN
        ↓               ↓
  UDISE VERIFY     PEN VERIFY
        ↓               ↓
  UDISE SHEET      PEN SHEET
      GREEN            GREEN
        ↓               ↓
       OGR UPDATED ONLY WHERE DEFINED
        ↓
ND RECONCILIATION WHEN REQUIRED
        ↓
FINAL VERIFIED STUDENT STATE
```

## 201.2 Automation state machine

The automation must model the student as a stateful record rather than as a sequence of blind clicks.

```text
READ_SHEETS
    ↓
VALIDATE_STUDENT_DATA
    ↓
SKIP_IF_ALREADY_GREEN
    ↓
DETERMINE_CLASS_ROUTE
    ↓
DETERMINE_ENTRY_CONDITION
    ↓
RUN_UDISE_BRANCH_IF_REQUIRED
    ↓
VERIFY_UDISE
    ↓
UPDATE_UDISE_SHEET / OGR UID
    ↓
RUN_PEN_BRANCH_IF_REQUIRED
    ↓
VERIFY_PEN
    ↓
UPDATE_PEN_SHEET / OGR PEN WHEN DEFINED
    ↓
CHECK_ND_RECONCILIATION_IF_REQUIRED
    ↓
LOG_FINAL_STATE
```

Each arrow represents a state transition that must be verified before the next state is committed.

---

# 202. THREE-SOURCE DATA MODEL — EXACT RESPONSIBILITY OF EACH FILE

## 202.1 OGR — Online General Register

OGR is the school's general register. It is the persistent school-side student record.

It is not to be renamed as a “master database” in future documentation because that terminology changes the meaning of the actual workflow.

OGR contains school-side information such as:

- Academic year
- Student name
- Class
- Mobile numbers
- PR / admission-related number
- DOB
- DOA
- DOE
- Aadhaar
- UID
- PEN
- APAAR
- Documents pending

OGR is used as a source and as a destination for selected government identifiers.

### Critical OGR rule

Government completion does **not** automatically mean that the OGR row becomes green.

The government-sheet green state and OGR visual state are separate concepts.

---

## 202.2 UDISE_Entry_(State)

This is the state/UDISE processing sheet.

A successful UDISE completion causes the **entire relevant UDISE row** to become GREEN.

UID/UDISE being populated is useful evidence, but it is not by itself sufficient proof that the entire UDISE workflow has been completed.

---

## 202.3 PEN_Entry_(National)

This is the national/PEN processing sheet.

A successful PEN workflow causes the **entire relevant PEN row** to become GREEN.

A valid 11-digit PEN is one possible successful result.

`PEN = ND` can also be a successful completed state when the national portal indicates that a PEN is not available at that point.

---

# 203. STUDENT IDENTITY AND MATCHING RULES

The automation must never depend on student name alone when a stronger combination is available.

Preferred identity/matching evidence should be based on the available combination of:

- Student name
- Father's name
- Mother's name where available
- DOB
- Aadhaar where legally and operationally appropriate
- GR / admission number
- Class
- Existing UID
- Existing PEN
- Source-school information for imports

For portal search results, the automation must not silently select the first matching student if multiple candidates exist.

Ambiguous matches must move to manual review.

---

# 204. UDISE WORKFLOW — REQUIRED DOCUMENTATION SHAPE

The confirmed UDISE New Entry workflow is documented across Sections 13–32 and the corresponding video timeline.

A future implementation specification must treat the workflow as the following ordered operation groups:

```text
UDISE LOGIN / SCHOOL CONTEXT
        ↓
STUDENT NEW ENTRY
        ↓
BIRTH-DATA ROUTE
        ├── CRS-RGI
        └── MANUAL
        ↓
GET / SUBMIT BIRTH DETAILS
        ↓
CTS STUDENT DETAILS
        ↓
ADD NEW STUDENT
        ↓
MANAGE STUDENTS
        ↓
PERSONAL PROFILE
        ↓
EDUCATION PROFILE
        ↓
BANK PROFILE
        ↓
SCHOLARSHIP & FACILITY
        ↓
HEALTH & CWSN
        ↓
FINAL SAVE
        ↓
VERIFY COMPLETE PROFILE
        ↓
UDISE SUCCESS
```

For every group, the developer must preserve the exact field observations already recorded in this context file and must use live DOM inspection for final selectors.

---

# 205. UDISE — BIRTH ROUTE DECISION

The birth-information stage has two observed routes.

## Route A — CRS-RGI

Observed information includes:

- BRN
- Birth Year
- Birth Month
- Birth Date
- Gender
- `GET DETAILS FROM CRS-RGI`

The automation must not assume that CRS-RGI succeeds for every student.

If the portal does not return the required details, the documented manual route may be required depending on the actual portal state and authorized operator action.

## Route B — Manual

Observed fields include:

- Birth State
- Birth District
- Birth Taluka
- Birth City/Place
- Birth Village
- Year
- Month
- Date
- BRN
- Birth Certificate Number
- Birth Certificate PDF upload
- Next

Dependent geographic fields must be handled sequentially and verified after selection.

---

# 206. UDISE — PROFILE COMPLETION RULE

The UDISE workflow is not complete merely because:

- the student was created,
- the Add Student button succeeded,
- a UID appeared,
- a page loaded without an obvious error, or
- one profile tab was saved.

Completion requires the relevant pending profile sections to be completed and the final save/completion state to be verified.

The relevant observed profile areas are:

1. Personal
2. Education
3. Bank
4. Scholarship & Facility
5. Health & CWSN

Fields that are genuinely non-applicable may use the portal's legitimate NA/blank/non-applicable behavior where supported. The automation must not invent values simply to satisfy a form.

---

# 207. AFTER-UDISE HANDOFF — OPERATIONAL CHECKLIST

Before the automation starts normal PEN processing, it must establish the following checkpoint:

### Required facts

- Correct student identified.
- Correct class identified.
- Correct class-based login route identified.
- UDISE branch has completed.
- UDISE completion has been independently verified.
- UDISE row is GREEN.
- OGR UID contains the actual resulting UID.
- OGR color remains unchanged.
- PEN has not incorrectly been treated as completed merely because UDISE succeeded.
- PEN condition is known: New, Import, Other State, or already available/imported.

### If all are true

Continue to the correct PEN branch.

### If any are false

Do not continue blindly. Log the inconsistency and move to the appropriate recovery/manual-review state.

---

# 208. PEN NEW ENTRY — REQUIRED DOCUMENTATION SHAPE

The confirmed New PEN workflow is:

```text
NATIONAL UDISE+ SCHOOL CONTEXT
        ↓
NEW STUDENT ENTRY / INITIALIZATION
        ↓
INITIAL SAVE
        ↓
SUCCESS MODAL
        ↓
GENERAL PROFILE
        ↓
ENROLMENT PROFILE
        ↓
FACILITY PROFILE
        ↓
PROFILE PREVIEW / COMPLETION
        ↓
DATA COMPLETION IS COMPLETE
        ↓
PEN RESULT READ
        ↓
PEN SHEET UPDATE
        ↓
PEN ROW GREEN
```

The portal's initialization success message is not the same as final profile completion.

---

# 209. PEN — INITIALIZATION VS FINAL COMPLETION

The New PEN workflow contains two different success concepts.

## Initialization success

The portal displays a success modal stating that the student has been initialized/saved successfully, with options including:

- Add New Student
- Go to New Entry List
- Fill General Profile

This confirms that the student initialization step succeeded.

It does **not** by itself prove that the full PEN profile is complete.

## Final completion

The later completion state is represented by the portal message:

`Data completion is complete.`

Only after this final state is verified should the automation commit the PEN sheet as GREEN.

---

# 210. PEN — PROFILE GROUPS TO PRESERVE

## General Profile

Observed categories include:

- Guardian information
- Aadhaar information
- Name as per Aadhaar
- Admission date
- Primary/alternate mobile
- CWSN information
- Address
- Pincode
- Email
- Mother tongue
- Social category
- Religion
- BPL
- AAY
- EWS/disadvantaged status
- CWSN

## Enrolment Profile

Observed categories include:

- Admission number
- Admission date
- Class
- Roll number
- Medium
- Language group
- Foreign language area
- Mandatory/general subjects
- Additional subjects
- Co-curricular subjects
- Previous academic status
- Previous class
- RTE 12C
- RTE amount
- Previous result
- Previous class percentage
- Attendance days

## Facility Profile

Observed categories include:

- Competitions/olympiads
- NCC/NSS/Scouts & Guides
- Height
- Weight
- Distance to school
- Highest education level of mother/father/legal guardian

Exact live field names and selectors must be verified against the current portal DOM before production implementation.

---

# 211. AADHAAR CONSENT — CONTROLLED HUMAN STEP

The observed national portal can display a demographic-authentication consent dialog:

`CONSENT FOR DEMOGRAPHIC AUTHENTICATION`

with an `I Agree` action.

The automation specification must treat this as a controlled/manual interaction unless the school has an explicitly authorized process permitting automated handling.

The automation must never silently manufacture consent.

The event should be logged as a human-confirmation checkpoint where applicable.

---

# 212. PEN RESULT SEMANTICS

There are three concepts that must remain separate:

### Actual PEN

An 11-digit PEN exists and can be recorded.

### Portal NA

The national portal indicates that a PEN is not available.

### Spreadsheet ND

The school's spreadsheet representation of the portal's unavailable/not-defined state.

Therefore:

```text
Portal NA
   ↓
Spreadsheet ND
```

This is not the same thing as an automation failure.

---

# 213. ND RECONCILIATION — COMPLETE DECISION FLOW

ND reconciliation is a later, separate operation.

```text
PEN SHEET = ND
        ↓
OPEN NATIONAL UDISE+ STUDENT DATABASE
        ↓
SELECT CORRECT CLASS FIRST
        ↓
SEARCH STUDENT BY NAME
        ↓
READ ALL RELEVANT MATCHES
        ↓
MATCH CORRECT STUDENT
        ↓
READ CURRENT PEN
        ↓
      ┌───────────────┐
      │               │
  11-DIGIT PEN       NO PEN
      │               │
      ↓               ↓
UPDATE PEN SHEET   KEEP ND
      ↓
UPDATE OGR PEN
```

If multiple candidates exist and the available data cannot distinguish them safely, the automation must stop and request manual identification.

It must not select the first result merely because it appears first.

---

# 214. IMPORT BRANCHES — WHAT IS KNOWN AND WHAT IS NOT

The four business conditions are confirmed as:

1. New UDISE + New PEN
2. New UDISE + PEN Import
3. UDISE already available/imported + New PEN
4. UDISE + PEN both imported

However, the exact click-by-click import workflows are **not confirmed** in the currently analyzed source material.

Therefore the context file deliberately does not invent:

- Import menu sequence
- Import search sequence
- Source-school selection behavior
- Other-State import behavior
- Major-change workflow
- Exact matching confirmation screen
- Import status transitions
- Exact green transition for each import case
- Exact combined Condition 4 order

These must be documented from the dedicated UDISE Import and PEN Import/Other State recordings before production implementation.

---

# 215. IMPORT DATA — INFORMATION THAT MUST BE CAPTURED FROM THE REMAINING VIDEOS

When the remaining videos are analyzed, the documentation must record every observable transition using this exact structure:

```text
TIMESTAMP / ORDER
SCREEN NAME
CURRENT RECORD STATE
ACTION PERFORMED
EXACT CONTROL / BUTTON / FIELD
INPUT VALUE SOURCE
PORTAL RESPONSE
NEW SCREEN / MODAL / MESSAGE
DATA CREATED OR CHANGED
SPREADSHEET CHANGE
ROW COLOR CHANGE
STATUS CHANGE
ERROR / WARNING
WHAT USER DID TO RECOVER
FINAL RESULT
NEXT STATE
```

The analysis must also capture:

- Search terms used
- Which student was selected when duplicates existed
- Whether a confirmation modal appeared
- Whether the imported student's existing government ID was displayed
- Whether the school/source information was shown
- Whether the portal used ACTIVE/INACTIVE/IMPORT PENDING or another status
- Whether the portal allowed editing after import
- Whether a successful import immediately turns a row GREEN
- Whether OGR changes during import
- Whether imported records bypass New Entry steps
- Whether import can be resumed after interruption

---

# 216. SCREEN-BY-SCREEN DOCUMENTATION STANDARD

For every future portal screen, the context file should use a compact but descriptive record like this:

### Screen record template

**Screen purpose:** What business task this screen performs.

**How reached:** The exact preceding action/state.

**Visible controls:** Relevant buttons, tabs, fields, dropdowns, tables, modals.

**Input source:** Which spreadsheet field supplies each value.

**User action:** Exactly what the operator does.

**Portal response:** What changes visually after the action.

**Verification:** How success is established.

**Data consequence:** What record is created/updated.

**Spreadsheet consequence:** Which cell/row/status/color changes.

**Failure:** What can go wrong or was actually observed to go wrong.

**Recovery:** What the operator did or what automation should do.

**Next state:** Exact next workflow state.

This is the minimum acceptable description for future video-derived workflow sections.

---

# 217. OBSERVED PROBLEMS MUST BE PRESERVED

The context file must never document only the happy path.

If a recording shows:

- wrong dropdown selection,
- failed lookup,
- missing birth record,
- validation message,
- unexpected blank field,
- session issue,
- duplicate search result,
- wrong student selection risk,
- portal delay,
- save failure,
- modal that blocks the next step,
- field that must be manually corrected,
- or any other operational problem,

the context file must record:

1. what was attempted,
2. what appeared,
3. why it was a problem,
4. what the user did next,
5. what finally worked,
6. what the automation should detect,
7. whether human intervention is required.

A problem that is visible in a source recording must not disappear from the final automation specification.

---

# 218. VERIFICATION IS A FIRST-CLASS OPERATION

Every write to a spreadsheet status must follow a verified portal outcome.

Bad pattern:

```text
Click Save
↓
Assume success
↓
Turn row GREEN
```

Required pattern:

```text
Click Save
↓
Wait for expected portal response
↓
Inspect response / modal / status / record
↓
Confirm expected data exists
↓
Only then commit spreadsheet state
```

If verification fails, the row must not be marked GREEN.

---

# 219. RESUME / CRASH-SAFE DESIGN

The automation must be able to stop at any meaningful checkpoint and continue without duplicating government records.

A checkpoint should identify at minimum:

- Student identity
- Source sheet/tab
- Source row
- Entry condition
- Class route
- Current portal
- Current workflow stage
- Last verified successful operation
- Spreadsheet update state
- Retry count
- Error/manual-review state
- Timestamp

The application should be able to distinguish:

```text
NOT STARTED
IN PROGRESS
PORTAL ACTION COMPLETED BUT NOT VERIFIED
VERIFIED COMPLETED
MANUAL REVIEW REQUIRED
FAILED / RETRYABLE
FAILED / NON-RETRYABLE
```

These internal states must not be confused with government portal status labels.

---

# 220. FINAL AUTOMATION IMPLEMENTATION CONTRACT

Before coding the production application, the implementation team must have the following artifacts:

### A. Source data contract

Exact columns and semantics for:

- OGR
- UDISE PH1/PH2/PH3
- PEN PH1/PH2/PH3
- PEN IMPORT PENDING

### B. Routing contract

Exact class normalization and class-to-login routing.

### C. Condition contract

Exact detection logic for all four entry conditions.

### D. UDISE New Entry contract

Confirmed screen-by-screen sequence, field mappings, verification rules, and failure handling.

### E. PEN New Entry contract

Confirmed screen-by-screen sequence, field mappings, verification rules, consent handling, and failure handling.

### F. ND contract

Confirmed reconciliation search, matching, update, and no-PEN behavior.

### G. Import contract

This remains incomplete until the two remaining recordings are analyzed.

### H. State contract

Exact internal automation states and allowed transitions.

### I. Spreadsheet update contract

Exact conditions under which:

- UID is written,
- PEN is written,
- UDISE row becomes GREEN,
- PEN row becomes GREEN,
- OGR is updated,
- OGR color remains unchanged.

### J. Safety contract

Human confirmation requirements, credential handling, Aadhaar consent handling, manual-review rules, and ambiguous-match rules.

### K. Recovery contract

Retry, resume, session recovery, screenshot/logging, and manual intervention.

### L. Testing contract

At minimum test:

- New/New
- New UDISE + PEN Import
- Existing/imported UDISE + New PEN
- Both imported
- PEN = ND
- ND later becomes actual PEN
- Already GREEN row
- Duplicate portal search result
- UDISE failure
- PEN failure
- Browser/session timeout
- Partial save
- Application crash/resume
- Manual intervention checkpoint

---

# 221. FINAL COVERAGE STATUS — WHAT THIS CONTEXT FILE CONTAINS

## Fully documented / confirmed at project level

- Project objective
- Source-data preparation workflow
- Three operational spreadsheets/files
- OGR structure and semantics
- UDISE sheet structure
- PEN sheet structure
- PEN IMPORT PENDING structure
- PH1/PH2/PH3 meaning
- UID/UDISE terminology
- PEN terminology
- ND/NA mapping
- GREEN semantics
- OGR color semantics
- Four entry conditions
- Class-based routing
- UDISE New Entry flow
- UDISE birth routes
- UDISE profile areas
- UDISE completion principle
- After-UDISE handoff state
- PEN New Entry flow
- PEN initialization vs final completion
- PEN profile stages
- Aadhaar consent checkpoint
- PEN ND successful state
- ND reconciliation flow
- Matching safety rules
- State-driven automation architecture
- Data normalization requirements
- Field mapping approach
- Selector strategy
- Dropdown/dependent-dropdown strategy
- File upload requirement
- Session handling
- Logging
- Retry/resume
- Manual intervention
- Security boundaries
- Google Cloud role
- Example-data non-hardcoding rule
- Existing-GREEN skip rule

## Still source-dependent / must not be invented

- Exact UDISE Import click-by-click workflow
- Exact PEN Import click-by-click workflow
- Exact Other State PEN workflow
- Exact major-change workflow
- Exact import matching confirmation behavior
- Exact import status transitions
- Exact import GREEN rules
- Exact Condition 4 combined sequence
- Exact final production selectors/DOM attributes
- Any portal behavior that may have changed since the recordings

---

# 222. FINAL RULE FOR FUTURE CONTINUATION

When this context file is opened in a new conversation, the next assistant/developer should **not restart discovery from the beginning**.

It should first read this context file and understand:

1. what is already confirmed,
2. what is already implemented conceptually,
3. what is still unresolved,
4. which source recordings have already been analyzed,
5. which recordings remain to be analyzed,
6. which spreadsheet semantics are non-negotiable,
7. which workflow states must be preserved.

The next task should begin from the first unresolved item rather than repeating already-established discovery.

Most importantly:

> **Do not ask the user to re-explain the five already-analyzed videos.**

> **Do not invent the two unresolved import workflows.**

> **Do not convert examples into hardcoded application logic.**

> **Do not mark GREEN merely because a button was clicked.**

> **Do not treat ND as failure.**

> **Do not change OGR color merely because government processing completed.**

> **Do not treat UID generation as proof of complete UDISE profile completion.**

> **Do not treat PEN initialization as proof of final PEN completion.**

---

# 223. CONTEXT FILE QUALITY STANDARD

This context file is considered useful only if a technically competent person who did not participate in the original conversation can reconstruct the intended automation state machine from the document without relying on memory of the original discussion.

Where source evidence is detailed, the context file must be descriptive.

Where source evidence is incomplete, the context file must explicitly say `UNRESOLVED` rather than fabricate detail.

That distinction is intentional and is part of the project's correctness.

# END OF FINAL CRYSTAL-CLEAR AUDIT

# 224. COMPLETE CONTINUATION RECORD — PURPOSE OF THIS FILE

This document is not an archive, summary, report, or abbreviated handoff.

It is the **complete working context for continuing the Satyam Government Student Entry Automation project in a new ChatGPT/session**.

The purpose is continuity: a future session must be able to understand the project, the terminology, the spreadsheet structures, the observed portal workflows, the business rules, the automation requirements, the corrections made during discussion, and the unresolved evidence boundaries without requiring the user to reconstruct the project from memory.

The word "complete" in this context means: preserve all project information available from the conversation/source material that is relevant to continuing the work. It does not mean inventing observations that were never established.

The document must therefore preserve BOTH:

1. confirmed source-derived information; and
2. explicit unresolved boundaries.

An unresolved item is information, not a defect in the context file. It must remain unresolved until the relevant source is supplied/analyzed.

---

# 225. USER'S REQUIRED WORKING STYLE FOR THIS PROJECT

The user repeatedly required the following working style:

- Understand the workflow before coding.
- Do not jump prematurely to implementation.
- Ask one question at a time when additional discovery is required.
- Keep responses direct and practical.
- Preserve exact terminology used by the user.
- Do not silently reinterpret business terminology.
- Do not turn examples into hardcoded values.
- Do not guess missing portal behavior.
- Do not ask for a video again when it has already been analyzed and its findings are present in this context.
- When a workflow is source-derived, document what happened rather than summarizing it vaguely.
- When an observed problem occurred, preserve the problem and the recovery, because both affect automation design.
- The final application should be designed as a reliable workflow/state machine, not a blind coordinate/click macro.

The user wants the eventual automation to be understandable, maintainable, resumable, and safe for real school administrative use.

---

# 226. ORIGINAL BUSINESS PROCESS BEFORE AUTOMATION

The broader school process is:

```text
Student admission
        ↓
Documents requested from parent
        ↓
Documents received / verified
        ↓
Student information digitized
        ↓
Student becomes ready for government entry
        ↓
Student assigned to PH1 / PH2 / PH3 or another operational batch
        ↓
Data prepared in school import-format Excel
        ↓
Excel imported into school website/system
        ↓
Website Report section
        ↓
Staff selects students ready for government entry
        ↓
UDISE / State Excel generated
PEN / National Excel generated
        ↓
Government portal processing
        ↓
Verified completion
        ↓
Spreadsheet status updated
        ↓
Later ND reconciliation where required
```

The physical documents remain source/verification material. The government-entry stage uses structured digital records generated by the school workflow.

---

# 227. DOCUMENT REQUIREMENTS THAT MOTIVATED THE PHASE SYSTEM

The project discussion established that required documents can arrive at different times.

Examples discussed:

For JrKG–1st:
- Student Birth Certificate
- Student Aadhaar Card

For 2nd onward:
- Student Transfer Certificate (TC)
- Student Aadhaar Card

Additional parent documents collected include:
- Father Aadhaar Card
- Mother Aadhaar Card

The phase mechanism exists because students do not necessarily become ready at the same time.

PH1 / PH2 / PH3 mean operational batches/phases. They are not different database schemas and not different student formats.

---

# 228. THREE OPERATIONAL SPREADSHEET FILES

Exactly three operational spreadsheet files are central to the current workflow:

1. `ONLINE GENERAL REGISTER` — OGR
2. `UDISE_Entry_(State)`
3. `PEN_Entry_(National)`

The OGR is the school's general register where every student entry is recorded. It must not be described as the project's "master database" unless the user explicitly changes that terminology.

The UDISE workbook is the state/UDISE working dataset.

The PEN workbook is the national/PEN working dataset.

---

# 229. OGR — CONFIRMED ROLE AND FIELDS

The OGR is the general register.

The project has used the following OGR fields/columns during the workflow:

- AY
- NAME
- STD
- MOBILE 1
- MOBILE 2
- PR
- DOB
- DOA
- DOE
- AADHAR
- UID
- PEN
- T-GR
- TC
- APAAR
- DOCUMENTS PENDING

Not every visible column is populated at the same stage.

Initial/basic entry order discussed:

1. AY
2. NAME
3. STD
4. MOBILE 1
5. MOBILE 2
6. PR

Later fields include:

- DOB
- DOA
- DOE
- AADHAR
- UID
- PEN

Example observed student record:

- AY: `2026-27`
- NAME: `AISHA BISOYI`
- STD: `SR KG`
- MOBILE 1: `9337302202`
- PR: `P091`
- DOB: `02/01/2022`
- DOA: `18/05/2026`
- DOE: `23/09/2026`
- AADHAR: `617750014825`
- UID: `242241000672620025`

These are examples from the observed workflow and must never be hardcoded into production automation.

### OGR color rule

Government workflow completion does **not** turn the OGR row GREEN.

The OGR row color remains unchanged during UDISE/PEN government-entry completion.

This is a non-negotiable distinction.

---

# 230. UDISE WORKBOOK — EXACT STRUCTURE RECORDED

Workbook/file: `UDISE_Entry_(State)`

Tabs:

- PH1
- PH2
- PH3

Exact headers recorded:

1. REMARK
2. Class
3. UDISE No
4. Birth Cert Reg No
5. Birth Year
6. Birth Month
7. Birth Date
8. Gender
9. Birth State
10. Birth District
11. Birth City
12. Student Name
13. Father's Name
14. Mother's Name
15. Surname
16. Date of Birth
17. GR No
18. Roll No
19. Plot Number
20. Society
21. Landmark
22. Area
23. Pin Code
24. Mother Tongue
25. Date of Join
26. Aadhar Card No
27. Name as per Aadhar
28. Mobile No 1
29. Mobile No 2

PH3 may contain an additional blank/unused column.

### UDISE row completion color

When UDISE processing is successfully completed and verified, the **entire UDISE row** becomes GREEN.

It is not sufficient to color only the UDISE/UID cell.

---

# 231. PEN WORKBOOK — EXACT STRUCTURE RECORDED

Workbook/file: `PEN_Entry_(National)`

Tabs:

- PH1
- PH2
- PH3
- IMPORT PENDING

Main PH sheet headers:

1. PEN
2. Class
3. Student Father Surname
4. Gender
5. Date of Birth
6. Student State Code (UDISE No)
7. Mother's Name
8. Father's Name
9. Aadhar Number of Student
10. Name of Student as per Aadhar Card
11. Admission Date
12. Full Address
13. Pincode
14. Mobile No 1
15. Mobile No 2
16. Mother Tongue
17. Admission Number in Present School (GR No)
18. Roll No
19. Previous Class Percentage
20. Previous Class Attendance Days
21. Height (cm)
22. Weight (kg)

`IMPORT PENDING` headers:

- SR NO
- STUDENT NAME
- PEN
- DOB
- SCHOOL NAME
- SCHOOL UDISE
- STATE
- DISTRICT
- BLOCK
- HEADMASTER
- CONTACT NO
- STATUS
- REMARK

Example import-pending records were observed, including:

- `SOUMYA RANJAN BEHERA` — PEN `23060444551` — source school/status information including ACTIVE / IMPORT PENDING
- `REYANSH SURJYAMANI PATRA` — PEN `23428960733` — Gujarat / Surat / Surat Corpu.

These examples are illustrative and must not be hardcoded.

### PEN row completion color

When PEN workflow is successfully completed and verified, the **entire PEN row** becomes GREEN.

A successful completed PEN state can legitimately have:

```text
PEN = ND
PEN ROW = GREEN
```

---

# 232. UID / UDISE / PEN TERMINOLOGY

In this project:

- UID and UDISE are used interchangeably in the operational workflow.
- UDISE/UID is treated as an 18-digit value for this project.
- PEN is an 11-digit value when an actual PEN is available.
- The National UDISE+ portal can display `NA` for PEN when it is not available.
- The school spreadsheet uses `ND` for the corresponding not-defined/not-yet-available state.

Therefore:

```text
Portal NA
   ↓
Spreadsheet ND
```

Do not convert ND into a fake PEN.

Do not use UDISE/UID as PEN.

Do not generate a random placeholder.

---

# 233. CLASS ROUTING — NON-NEGOTIABLE PROJECT RULE

Class determines which school/government login workflow is used.

Group A:

```text
JrKG
SrKG
Balvatika
1st
```

→ Satyam School ID workflow.

Group B:

```text
2nd onward
```

→ Block ID workflow.

This routing applies to both UDISE and PEN processing.

The exact live login implementation remains subject to portal verification/configuration and must not be invented from the class rule alone.

Class normalization must support variants such as:

- JR KG
- JrKG
- SR KG
- Sr.KG
- Balvatika
- 1st
- LKG/KG1/PP2
- UKG/KG2/PP1
- portal class codes such as `102-Sr.KG`

The automation should normalize these to a canonical internal class representation before routing.

---

# 234. FOUR ENTRY CONDITIONS — CENTRAL DECISION MODEL

The system has four operational combinations:

| Condition | UDISE | PEN |
|---|---|---|
| 1 | New | New |
| 2 | New | Import |
| 3 | Import | New |
| 4 | Import | Import |

### Condition 1

New UDISE + New PEN.

This is the fully observed normal New/New flow.

### Condition 2

New UDISE + PEN Import.

UDISE New Entry is known.

The exact PEN Import/Other State process remains source-dependent.

### Condition 3

UDISE Import + New PEN.

New PEN process is known.

The exact UDISE Import process remains source-dependent.

### Condition 4

UDISE Import + PEN Import.

Both import branches remain source-dependent.

Do not infer Condition 4 by simply concatenating assumptions about the two import workflows.

---

# 235. VIDEO / SOURCE INVENTORY

Five recordings have already been analyzed:

1. `GOOGLE SHEET.mp4`
2. `GUJARAT ENTRY.mp4`
3. `AFTER UDISE ENTRY BEFORE PEN .mp4`
4. `PEN ENTRY.mp4`
5. `5 ND MANUAL UPDATE.mp4`

Approximate observed lengths discussed:

- GOOGLE SHEET.mp4 — ~1:55
- GUJARAT ENTRY.mp4 — ~10:44
- AFTER UDISE ENTRY BEFORE PEN .mp4 — ~2:03
- PEN ENTRY.mp4 — ~6:15
- 5 ND MANUAL UPDATE.mp4 — ~1:52

Two dedicated recordings remain the evidence source for the missing branches:

- UDISE Import
- PEN Import / Other State

The five already analyzed videos must not be requested again simply because the conversation changes.

---

# 236. VIDEO 1 — GOOGLE SHEET WORKFLOW

The recording establishes the spreadsheet-side staging environment and the relationship among the three working sheets/files.

The important operational concept is:

```text
OGR
↓
UDISE working sheet
↓
PEN working sheet
```

The OGR is the general register and the government-specific workbooks are separate operational datasets.

The spreadsheet workflow supports staged processing and later portal entry.

The automation must therefore preserve source row identity and should never rely only on visible row position because rows can change as sheets are edited.

Student matching should use stable identifying fields and normalized values.

---

# 237. VIDEO 2 — GUJARAT UDISE NEW ENTRY: PORTAL CONTEXT

Observed portal/workflow context:

- Gujarat Child Tracking System / Gujarat UDISE environment.
- School context: SATYAM STARS INTERNATIONAL SCHOOL.
- Left navigation observed included items such as:
  - Home
  - Manage Students
  - Student Tracking Report
  - Student Transfer Request List
  - GSRSE Voucher
  - Back To School Phase2
  - Attendance Report
  - Student Identity (SID) Number Entry
  - Early Warning System
  - Add Local Holiday
  - and other portal functions.

The workflow enters a Student New Entry and then completes the student's profile.

---

# 238. UDISE NEW ENTRY — BIRTH ROUTE 1: CRS-RGI

Observed birth-entry route:

Fields/actions include:

- BRN
- Birth Year
- Birth Month
- Birth Date
- Gender
- `GET DETAILS FROM CRS-RGI`

The automation must treat this as a distinct birth route from the manual birth-information route.

Do not mix the two routes unless the portal itself requires a fallback.

---

# 239. UDISE NEW ENTRY — BIRTH ROUTE 2: MANUAL

Observed manual route includes:

- Birth State
- Birth District
- Birth Taluka
- Birth City/Place
- Birth Village
- Year
- Month
- Date
- BRN
- Birth Certificate No.
- PDF upload
- Next

Example observed data:

- Birth State: Odisha
- Birth District: Ganjam
- Birth Taluka: Sheragada
- Year: 2022
- Month: January
- Date: 02
- BRN: `13/2022`
- Birth certificate PDF uploaded

These are observed examples only.

The automation must source values from the student record/document workflow rather than hardcoding them.

The exact maximum PDF size should be obtained from the live portal/DOM and must not be guessed.

---

# 240. UDISE NEW ENTRY — GENDER AND CTS CREATION

Gender dropdown observed:

- Male
- Female
- Other

After the birth/student creation stage, CTS/new-student fields include:

- Student name
- Father name
- Mother name
- Surname
- DOB
- Disabled yes/no
- Disability type

The student is created using:

`ADD NEW STUDENT`

The automation must verify that the student was actually created rather than treating the click itself as success.

---

# 241. UDISE MANAGE STUDENTS — OBSERVED LIST

The Manage Students list displayed information such as:

- Aadhaar/UID
- Student Name
- Father Name
- Mother Name
- Surname
- DOB
- DOA
- GR No
- Section
- Status
- Edit

This list can be used as a verification surface and/or lookup surface.

The automation should not assume the first result is the correct student when multiple students match.

---

# 242. UDISE STUDENT PROFILE — MAIN SECTIONS

Observed profile sections:

1. Personal
2. Education
3. Bank
4. Scholarship & Facility
5. Health & CWSN

The workflow must treat completion of the relevant sections as the actual UDISE task, not merely creation of the initial CTS record.

---

# 243. UDISE PERSONAL SECTION — OBSERVED FIELDS / EXAMPLE

Observed example values for Aisha included:

- Student: `AISHA`
- Father: `TOFAN`
- Mother: `PRIYANKA`
- Surname: `BISOYI`
- Guardian: `TOFAN BISOYI`
- Area/locality: `PANDESARA`
- District/code context: `2422-SURAT`
- District/corporation: `SURAT CORPO.`
- Society/address element: `SHREE RAMNAGAR`
- Road: `BAMROLI ROAD`
- PIN: `394221`
- Mother tongue: `12-Odia`
- DOB: `02/01/2022`
- Gender: `2-Girl`
- Category: `1-General`
- Religion: `11-General`

Observed bottom actions:

- `SAVE STUDENT`
- `CLEAR`

The automation should save and verify after the relevant section rather than blindly progressing.

---

# 244. UDISE EDUCATION SECTION

Observed education fields around the later field numbering included admission and academic information.

Examples:

- Admission number / GR context
- Admission date
- Class
- RTE
- Previous academic status/result
- Percentage
- Attendance
- Medium/language/subjects

Observed example:

- PR / admission context: `P091`
- Roll/admission: `91`
- Admission date: `18/05/2026`
- Class: `102-Sr.KG`
- Medium: English

Class dropdown observed:

- PP-3
- PP-2
- PP-1
- I
- II
- III
- IV
- V
- VI
- VII
- VIII
- IX
- X
- XI
- XII

Education also includes language/subject selection such as:

- mandatory/general
- additional
- co-curricular

Dependent options must be handled after the class/medium/language selection when applicable.

---

# 245. UDISE BANK SECTION

Bank fields were observed around fields 42–46.

The project explicitly states that values may be:

- NA
- blank
- non-applicable

The automation must not invent bank information merely to satisfy a form.

If the portal requires a non-applicable value, use the portal's valid non-applicable representation only when that representation is confirmed.

---

# 246. UDISE SCHOLARSHIP & FACILITY

The section exists and is part of the profile completion workflow.

Some exact field mapping was not sufficiently readable in the surviving source description.

Therefore:

`UNRESOLVED — exact field-by-field mapping must be verified from the live DOM/source material.`

Do not fabricate field names or values.

---

# 247. UDISE HEALTH & CWSN

Observed area around fields 62–81 includes:

- CWSN status
- disability/impairment
- UID/UDID
- learning disability
- dysgraphia
- dyscalculia
- dyslexia
- ASD
- ADHD
- intellectual/developmental disability
- folic/iron facilities
- vitamin A facilities
- other health/CWSN-related fields

The exact numbering and final DOM mapping require live verification.

Dependent controls must be handled according to selected CWSN/disability status.

---

# 248. UDISE FINAL SAVE AND COMPLETION RULE

The final operation is:

`SAVE STUDENT`

But the automation must not equate the click with completion.

Required state transition:

```text
Profile fields entered
↓
Save submitted
↓
Portal response observed
↓
Expected student/profile persistence verified
↓
UDISE completion accepted
↓
Entire UDISE row GREEN
```

The 18-digit UID appearing in the record is not sufficient by itself.

---

# 249. AFTER-UDISE RECORD STATE — DETAILED HANDOFF

This state is the bridge between UDISE processing and PEN processing.

The state means:

1. The student's UDISE/State processing has been completed and verified.
2. The UDISE workbook row is GREEN.
3. The student's UID/UDISE value is now available in the school data.
4. The OGR UID field is populated with the verified UID/UDISE.
5. The OGR row color remains unchanged.
6. The PEN process is still a separate state.
7. Depending on the student's entry condition, PEN may be:
   - New/pending,
   - Import/available through another workflow,
   - ND/not yet available,
   - or already imported/known.

The automation must therefore not interpret "UDISE complete" as "PEN complete."

### Required post-UDISE state check

After verified UDISE completion:

```text
UDISE row = GREEN?
       ↓ yes
UID/UDISE available?
       ↓ yes
OGR UID synchronized?
       ↓ yes / verify
OGR color unchanged?
       ↓ yes
Determine PEN condition
       ↓
Proceed to appropriate PEN branch
```

If UDISE verification fails, PEN processing must not proceed as though UDISE were complete.

---

# 250. PEN NEW ENTRY — NATIONAL UDISE+ CONTEXT

Observed national portal context:

`sdms.udiseplus.gov.in/g2/#/school/...`

The current configured portal URL should be treated as configuration rather than hardcoded to a potentially changing route.

Observed school context:

- UDISE code: `24224100067`
- Category: `1 Primary`
- Type: `3 Co-educational`
- Management: `5 Pvt. Unaided (Recognized)`
- Class context: Nursery/KG/PP3-5
- School: SATYAM STARS INTERNATIONAL SCHOOL
- AY: 2026-27

Observed user name:

`SUNIL PRADHAN`

Credentials must never be hardcoded into the application.

---

# 251. PEN NEW ENTRY — STUDENT INITIALIZATION

Observed example:

- Student: `AISHA TOFAN BISOYI`
- Class: `LKG/KG1/PP2`
- Section: `A`
- DOB: `02/01/2022`

After initialization/save, the portal displayed a success modal similar to:

`The Student has been initialised/Saved Successfully.`

It included:

- Student Name
- Class

Buttons included:

- `Add New Student`
- `Go to New Entry List`
- `Fill General Profile`

This modal is an important automation verification point.

The automation should inspect the modal and confirm the correct student before proceeding.

---

# 252. PEN WORKFLOW STAGES

The observed stages are:

1. General Profile
2. Enrolment Profile
3. Facility Profile
4. Profile Preview

The header can display:

- Permanent Education Number — Not Defined
- Student AADHAAR Verified
- CWSN No
- Impairment Type NA

`Permanent Education Number - Not Defined` is not automatically an error during New PEN processing.

---

# 253. PEN GENERAL PROFILE

Observed fields include:

- guardian name
- Aadhaar
- name as per Aadhaar
- admission date
- primary mobile
- alternate mobile
- CWSN
- address
- pincode
- email
- mother tongue
- social category
- religion
- BPL
- AAY
- EWS/disadvantaged
- CWSN

Observed address example:

`183, SHREE RAMNAGAR, BAMROLI ROAD, PANDESARA, Surat, Gujarat, 394221`

PIN:

`394221`

Mobile:

`9337302202`

Mother tongue:

`114-ODIA - Odia`

Category:

`1-GENERAL`

Religion options observed included:

- Muslim
- Christian
- Sikh
- Buddhist
- Parsi
- Jain
- NA

Again, observed values are examples and not constants.

---

# 254. AADHAAR CONSENT CHECKPOINT

The portal displayed a consent dialog titled:

`CONSENT FOR DEMOGRAPHIC AUTHENTICATION`

with an:

`I Agree`

action.

This is a controlled/manual safety point unless the school explicitly authorizes the exact automated consent action under its applicable process.

The automation must not silently automate a legally meaningful consent action merely because the button is technically clickable.

---

# 255. PEN ENROLMENT PROFILE

Observed enrolment information includes:

- Admission number, e.g. `P089`
- Admission date, e.g. `18/05/2026`
- Class
- Roll
- Medium, e.g. `19-English`
- Languages group, e.g. English
- Foreign language area
- Mandatory/general subjects
- Additional subjects
- Co-curricular subjects
- Previous academic status, e.g. `1-Studied at Current/Same School`
- Previous class
- RTE 12C yes/no
- RTE amount
- Previous result
- Previous class percentage
- Attendance days

Dependent subject choices must be handled according to the selected class/medium/language.

---

# 256. PEN FACILITY PROFILE

Observed facility information includes:

- competitions/olympiads yes/no
- NCC/NSS/Scouts & Guides
- height, e.g. `105 cm`
- weight, e.g. `45 kg`
- distance to school, e.g. `1-Less than 1 km`
- highest education level of mother
- highest education level of father
- highest education level of legal guardian

The section has Save/Next behavior and validation.

The automation must use actual student/source values where required and must not fabricate values such as height/weight.

---

# 257. PEN FINAL COMPLETION SIGNAL

The final observed modal is:

`Data completion is complete.`

with:

- `Okay`
- `Back to Student Dashboard`

This is a critical completion signal for the New PEN workflow.

After this signal is verified:

```text
PEN workflow completed
↓
PEN sheet updated
↓
PEN row GREEN
```

The PEN may still be `ND` at this point.

Therefore:

```text
PEN = ND + GREEN
```

is a valid successful New PEN result.

---

# 258. PEN PORTAL STATUS MODEL

The portal list can display:

- Not Started
- In-Progress
- Completed

It can also show stage indicators such as:

- GP
- EP
- FP

These portal statuses must not be blindly equated with spreadsheet color state.

The automation should use portal status as evidence but still apply its own verification rules before writing GREEN.

---

# 259. ND RECONCILIATION — PURPOSE

ND checking is a separate later operation.

It is not simply an automatic continuation of every New PEN flow.

The purpose is to find out whether a student whose spreadsheet PEN is `ND` now has an actual PEN in the national UDISE+ Student Database.

---

# 260. ND RECONCILIATION — EXACT OBSERVED SEQUENCE

1. Open the national UDISE+ Student Database.
2. Select the correct class **first**.
3. Search for the student by name.
4. Inspect the returned student(s).
5. Match the correct student.
6. Read the current PEN.
7. If an actual 11-digit PEN exists, update the PEN sheet and OGR.
8. If no actual PEN exists, keep `ND`.

The automation must not silently choose the first search result when multiple candidates exist.

Matching should use available corroborating fields such as:

- student name
- gender
- DOB
- class
- other available identifiers

If ambiguity remains, route to manual review.

---

# 261. ND RECONCILIATION — OBSERVED ACTUAL PEN EXAMPLES

One observed student transitioned from:

`ND`

to:

`23613114903`

Another observed student showed:

`23584566926`

These are examples of actual 11-digit PEN values observed during the reconciliation recording, not hardcoded values.

---

# 262. ND RECONCILIATION — NO PEN FOUND

If the national portal still shows `NA` or otherwise does not expose an actual PEN:

```text
Keep spreadsheet PEN = ND
```

Do not:

- invent a number,
- copy UID/UDISE into PEN,
- copy school code,
- use a temporary fake PEN.

---

# 263. ND RECONCILIATION — OGR UPDATE

The dedicated ND recording establishes that when an actual PEN becomes available:

```text
PEN sheet: ND → actual 11-digit PEN
OGR: ND/blank → actual 11-digit PEN
```

The exact implementation timing/transaction order should still be designed so both updates are consistent and recoverable.

A partial update should be logged and recoverable rather than silently ignored.

---

# 264. ALREADY-GREEN RULE

An already-GREEN row is considered completed by default.

The automation should skip it during normal batch processing unless the operator explicitly requests a re-check/reprocess operation.

A GREEN row must not be overwritten merely because the application is run again.

If a user deliberately requests reprocessing, the application should record that as an explicit operator action.

---

# 265. VERIFICATION-FIRST RULE

The project explicitly rejects:

```text
Click Save
↓
Assume success
↓
Mark GREEN
```

Required model:

```text
Perform action
↓
Wait for expected response
↓
Inspect response/modal/status/record
↓
Confirm expected data persisted
↓
Commit spreadsheet state
```

If verification fails:

- do not mark GREEN;
- preserve error state;
- capture evidence where possible;
- retry only when safe;
- otherwise route to manual review.

---

# 266. PARTIAL/FAILED STATES

The automation must distinguish at least:

- NOT STARTED
- IN PROGRESS
- PORTAL ACTION COMPLETED BUT NOT VERIFIED
- VERIFIED COMPLETED
- MANUAL REVIEW REQUIRED
- FAILED / RETRYABLE
- FAILED / NON-RETRYABLE

These are internal application states.

They must not be confused with government portal labels such as `Not Started`, `In-Progress`, or `Completed`.

---

# 267. STATE-DRIVEN AUTOMATION MODEL

Proposed conceptual states:

```text
READ_SHEETS
↓
VALIDATE_STUDENT
↓
DETERMINE_CLASS_ROUTE
↓
DETERMINE_ENTRY_CONDITION
↓
RUN_UDISE_BRANCH
↓
VERIFY_UDISE
↓
RUN_PEN_BRANCH
↓
VERIFY_PEN
↓
UPDATE_SHEETS
↓
LOG_SUCCESS
```

Separate operation:

```text
CHECK_ND_PEN
↓
MATCH_STUDENT
↓
READ_CURRENT_PEN
↓
UPDATE_PEN_SHEET
↓
UPDATE_OGR
↓
VERIFY
```

Import branches must be inserted once their recordings are analyzed.

---

# 268. DATA NORMALIZATION

Before browser automation, the application should normalize:

- dates
- phone numbers
- Aadhaar numbers
- PEN values
- UDISE/UID values
- class names
- gender
- names
- missing values
- ND/NA representations

Dates should be represented internally in a stable date representation and formatted according to the destination portal.

Do not trust the visible Google Sheets date formatting as proof of the underlying date value.

This matters because the project encountered date-format issues such as `dd/mm/yyyy` being displayed/converted differently by tools such as Canva; the automation should similarly treat date semantics explicitly rather than assuming display text is authoritative.

---

# 269. FIELD-MAPPING ARCHITECTURE

Use:

```text
SOURCE SHEET
     ↓
NORMALIZED STUDENT OBJECT
     ↓
PORTAL FIELD MAP
     ↓
PORTAL FORM
```

Do not directly scatter spreadsheet column references throughout browser code.

A field mapping layer should support:

- UDISE fields
- PEN fields
- different class routes
- different workflow conditions
- portal-specific representations
- missing/non-applicable values

---

# 270. SELECTOR STRATEGY

Preferred selector order:

1. stable ID
2. name attribute
3. data-* attribute
4. accessible label
5. associated label
6. stable text
7. table row + column relationship
8. CSS/XPath only when necessary

Avoid brittle coordinates.

Avoid selectors based on incidental styling classes when a semantic selector exists.

Selectors must be verified against the live portal before production use.

Exact final DOM attributes are currently unresolved and should not be invented.

---

# 271. DROPDOWNS AND DEPENDENT CONTROLS

The automation must identify the dropdown semantically and select the correct option.

After selecting a parent field, it must wait for dependent controls to populate before attempting the child selection.

Examples:

```text
Birth State
↓
Birth District
↓
Birth Taluka
↓
Birth City/Village
```

Other dependent examples:

```text
Class / Medium
↓
Language / Subject options
```

```text
CWSN = Yes
↓
Disability / impairment options
```

```text
Category
↓
Related fields
```

The automation should verify that the intended option was actually selected.

---

# 272. FILE UPLOADS

The UDISE manual birth route includes birth certificate PDF upload.

The automation should:

1. verify the source file exists;
2. verify it belongs to the correct student;
3. upload through the actual file input;
4. wait for upload/validation response;
5. verify that the portal accepted the file;
6. handle size/type errors without falsely marking completion.

The exact maximum allowed file size must be verified from the live portal.

---

# 273. SESSION MANAGEMENT

Government portals may log out, expire, redirect, or reject actions.

The application should detect conditions such as:

- login/session expiry
- unexpected redirect
- unauthorized page
- login page appearing during a workflow
- missing school context

The application should pause safely, preserve state, and require appropriate re-authentication/manual intervention rather than blindly continuing.

Credentials must not be embedded in source code.

---

# 274. GOOGLE CLOUD BOUNDARY

Google Cloud is used only for official Google Sheets API configuration/authentication and related API access.

It is not the hosting environment for the Windows desktop automation application.

The intended desktop application remains local on Windows.

---

# 275. PROPOSED TECH STACK

The project direction discussed is:

- Python
- PySide6
- Playwright
- Google Sheets API
- SQLite
- PyInstaller

Roles:

### Python
Core application logic.

### PySide6
Windows desktop GUI.

### Playwright
Visible/headed browser automation and DOM interaction.

### Google Sheets API
Reading/writing the operational Google Sheets.

### SQLite
Local state, checkpoints, logs, retries, and recovery metadata.

### PyInstaller
Packaging the Windows desktop application.

These are engineering choices and may be refined; changing them does not change the confirmed source workflow.

---

# 276. VISIBLE / HEADED BROWSER REQUIREMENT

The browser should operate in a visible/headed mode for this project because:

- the workflow needs observation;
- manual intervention may be required;
- consent/checkpoint events may need human control;
- troubleshooting requires seeing the portal;
- the operator must be able to pause/resume when necessary.

The final implementation should not assume a fully hidden browser unless the user explicitly changes this requirement.

---

# 277. LOCAL LOGGING

The local application should record at minimum:

- timestamp
- student identifier
- student name where appropriate and securely handled
- class
- source sheet/tab
- source row
- entry condition
- class/login route
- UDISE result
- PEN result
- portal status
- spreadsheet update status
- error
- retry count
- manual-review state
- screenshot/evidence path when failure occurs
- current workflow state

Sensitive data should be minimized in logs.

Do not log credentials.

---

# 278. CHECKPOINT / RESUME MODEL

The application must survive interruption.

A checkpoint should identify:

- student
- source file/sheet/tab
- source row
- condition
- class route
- current portal
- workflow stage
- last verified operation
- spreadsheet update state
- retry count
- error state
- manual-review state
- timestamp

After restart, the application must determine whether a government action was already verified before attempting a potentially duplicating action.

This is particularly important when a save may have succeeded but the browser crashed before the application saw the confirmation.

---

# 279. MANUAL INTERVENTION CONTROLS

Proposed GUI operations include:

- Start
- Pause
- Resume
- Retry
- Skip
- Open Student
- Mark for Manual Review
- Re-check
- Check ND Students
- View Logs

These are proposed controls, not portal facts.

The user must be able to intervene when:

- multiple matching students exist;
- consent requires controlled human action;
- the portal presents an unexpected error;
- required data is ambiguous;
- a session expires;
- a field cannot be safely determined;
- an import workflow is not yet specified.

---

# 280. FAILURE POLICY

If any critical operation fails:

- do not turn the row GREEN;
- do not claim completion;
- save diagnostic state;
- capture screenshot/evidence where useful;
- preserve the student checkpoint;
- retry only if retry is safe and idempotent;
- otherwise mark for manual review.

Examples of failure classes:

- validation error
- duplicate student
- wrong student match
- save rejected
- session timeout
- portal unavailable
- unexpected navigation
- upload rejected
- dependent dropdown not populated
- completion confirmation missing
- spreadsheet update failure
- ambiguous search result

The final complete exception taxonomy remains a live-portal implementation task.

---

# 281. IMPORT WORKFLOW BOUNDARY — DO NOT GUESS

The following are deliberately unresolved:

- exact UDISE Import clicks;
- exact UDISE Import screen sequence;
- exact UDISE Import matching behavior;
- exact UDISE Import completion signal;
- exact UDISE Import GREEN behavior;
- exact PEN Import clicks;
- exact Other State workflow;
- exact PEN Import matching behavior;
- exact import status transitions;
- exact import GREEN behavior;
- exact major-change process;
- exact Condition 4 sequence.

The existing New Entry flow must remain unchanged when import-specific behavior is added.

Only the import-specific delta should be introduced after analyzing the dedicated recordings.

---

# 282. CONDITION-SPECIFIC AUTOMATION INTENT

### Condition 1 — New UDISE + New PEN

```text
Validate student
↓
Class route
↓
UDISE New Entry
↓
Verify full UDISE completion
↓
UDISE row GREEN
↓
PEN New Entry
↓
Initialize
↓
General Profile
↓
Enrolment Profile
↓
Facility Profile
↓
Profile Preview
↓
Verify "Data completion is complete."
↓
PEN row GREEN
```

PEN may be ND after successful completion.

### Condition 2 — New UDISE + PEN Import

```text
UDISE New Entry
↓
Verify UDISE
↓
PEN Import / Other State workflow
```

Exact PEN import steps unresolved.

### Condition 3 — UDISE Import + New PEN

```text
UDISE Import workflow
↓
Verify UDISE
↓
PEN New Entry
```

Exact UDISE import steps unresolved.

### Condition 4 — UDISE Import + PEN Import

```text
UDISE Import
↓
Verify
↓
PEN Import
↓
Verify
```

Exact sequence and interactions unresolved.

---

# 283. MAJOR-CHANGE / OTHER-STATE TERMINOLOGY

The project explicitly uses the concept of PEN Import for cases such as:

- already available as another-school student;
- Other State;
- major changes.

The exact portal mechanics for these categories are not yet source-established.

Do not collapse these into New PEN merely because a PEN already exists.

---

# 284. WHAT MUST NEVER BE HARDcoded

Never hardcode:

- portal usernames
- portal passwords
- OTPs
- student names
- student Aadhaar values
- UDISE/UID values
- PEN values
- phone numbers
- addresses
- example height/weight
- school-specific record values when they belong in source data

Configuration such as portal URL, school code, sheet IDs, and authorized account configuration should be externalized/configurable as appropriate.

---

# 285. DATA CONSISTENCY RULES

The application must maintain a clear relationship between:

```text
OGR student
UDISE row
PEN row
portal student record
```

A student must not be matched solely by row number across separate sheets.

Use a normalized identity/matching strategy based on available stable fields.

Potential matching fields include:

- normalized student name
- father name
- mother name
- DOB
- Aadhaar where appropriate and authorized
- GR/admission number
- class
- UID/UDISE
- PEN

**Resolved for PEN Import — Other School ACTIVE:** the matching method is
Aadhaar-availability check → duplicate-Aadhaar signal → `View Details` →
`Track By Details` (existing student + existing PEN) → `Global Student
Search` by Student PEN → verify identity on the returned result. See
"PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW" at the end
of this document. **Still unresolved:** the matching method for the
successful/Dropbox PEN Import outcome, and for UDISE Import's
successful/Dropbox outcome — neither is demonstrated by any recording.

---

# 286. TESTING MATRIX

The eventual application must test at least:

1. New/New
2. New UDISE + PEN Import
3. UDISE Import + New PEN
4. UDISE Import + PEN Import
5. New PEN resulting in ND
6. ND later becoming an actual PEN
7. Already-GREEN row
8. Duplicate search results
9. Wrong-student search result
10. UDISE validation failure
11. PEN validation failure
12. Session timeout
13. Browser crash
14. Save succeeded but confirmation not seen
15. Spreadsheet update failure
16. File upload failure
17. Dependent dropdown delay
18. Manual consent checkpoint
19. Manual review
20. Resume after interruption

---

# 287. ACCEPTANCE CRITERIA

The eventual application should not be considered complete merely because it can fill forms.

It must satisfy:

- correct student selection;
- correct class routing;
- correct entry-condition routing;
- correct field mapping;
- correct handling of dropdown dependencies;
- safe file uploads;
- visible browser operation;
- verified portal completion;
- correct GREEN behavior;
- OGR color preservation;
- ND semantics;
- reliable sheet synchronization;
- retry/resume;
- manual review;
- logging;
- no credential hardcoding;
- no fabricated data;
- no blind duplicate submissions.

---

# 288. SOURCE-DERIVED FACT VS ENGINEERING DESIGN

The context must distinguish two categories.

## Source-derived facts

These are supported by the analyzed videos, sheets, or explicit project discussion.

Examples:

- exact sheet headers;
- observed portal labels;
- observed button labels;
- observed modal text;
- observed ND behavior;
- observed GREEN behavior;
- class routing rule;
- OGR color behavior;
- observed field examples.

## Engineering design

These are proposed implementation mechanisms.

Examples:

- Python;
- PySide6;
- Playwright;
- SQLite;
- selector priority;
- checkpoint schema;
- retry architecture;
- GUI controls;
- normalized student object;
- internal state names.

Engineering design can evolve without rewriting source-derived facts.

---

# 289. LIVE-PORTAL VERIFICATION BOUNDARY

Even when a recording establishes a workflow, selectors and exact DOM attributes can change.

Therefore:

- observed labels should be preserved;
- exact selectors should be verified against the current portal;
- current portal behavior should be tested before production deployment;
- source-derived workflow semantics must not be confused with current DOM implementation details.

If a current portal differs from the recording, record the difference explicitly rather than silently changing the project specification.

---

# 290. NEXT-SESSION STARTING INSTRUCTION

When this file is provided in a new ChatGPT session, the first instruction should be interpreted as:

> This file contains the complete current project context for the Satyam Government Student Entry Automation project. Read it fully before responding. Preserve all terminology, workflow rules, spreadsheet structures, observed portal behavior, state semantics, and engineering constraints. Do not ask me to repeat the five already-analyzed recordings or the New Entry workflow. Identify only genuinely unresolved work. Do not invent the UDISE Import or PEN Import/Other State workflows; analyze those recordings when they are provided. Continue from the documented state.

The new session should then use the document as the working context and continue from the unresolved items.

---

# 291. FINAL CONTINUITY CHECK

The next session must know all of the following without asking the user to reconstruct them:

- What the project is.
- Why it exists.
- What the three spreadsheets are.
- What OGR means.
- What UDISE/UID means in this project.
- What PEN means.
- What ND and NA mean.
- What PH1/PH2/PH3 mean.
- How class routing works.
- What the four conditions are.
- What the New UDISE workflow does.
- What the post-UDISE state means.
- What the New PEN workflow does.
- What successful PEN=ND means.
- What ND reconciliation does.
- How actual PEN updates OGR.
- What turns UDISE rows GREEN.
- What turns PEN rows GREEN.
- What does not turn OGR GREEN.
- What must be verified before GREEN.
- What the automation state machine should accomplish.
- How the browser should be controlled.
- How data should be normalized.
- How errors should be handled.
- How recovery should work.
- Which actions require human control.
- Which information must never be hardcoded.
- Which workflows remain unresolved.

---

# 292. IMPORTANT: DO NOT REDUCE THIS CONTEXT IN FUTURE REWRITES

If this document is later revised, do not replace detailed sections with short summaries merely to reduce length.

When correcting a section:

1. preserve all previously confirmed details;
2. add the correction explicitly;
3. preserve the reason/context for the correction when known;
4. mark superseded statements clearly rather than deleting useful history;
5. never replace a click-by-click source description with a one-line summary;
6. never remove observed problems because the final workflow is now understood;
7. never replace source evidence with generic portal assumptions.

The goal is continuity and implementation fidelity, not brevity.

---

# 293. FINAL PROJECT PRINCIPLE

The automation is being designed from the real school workflow and observed portal behavior.

Therefore the controlling principle is:

```text
SOURCE EVIDENCE
      ↓
DETAILED WORKFLOW MODEL
      ↓
EXPLICIT STATE TRANSITIONS
      ↓
VERIFIED PORTAL ACTIONS
      ↓
VERIFIED SPREADSHEET UPDATES
      ↓
RECOVERABLE AUTOMATION
```

Not:

```text
SUMMARY
↓
GUESS
↓
BLIND CLICKS
↓
ASSUME SUCCESS
```

# END OF COMPLETE PROJECT CONTEXT

---

# 294. CRITICAL IMPORT OUTCOME MODEL — CONFIRMED PROJECT RULE

This section records an important clarification to the Import workflow model.

The Import workflow is NOT a single outcome.

For both UDISE Import and PEN Import, there are **two operational outcomes**:

1. **IMPORT SUCCESSFUL** — the student is successfully imported because the student is in the **Dropbox of the other school**.
2. **IMPORT UNSUCCESSFUL / IMPORT PENDING** — the student is still **ACTIVE in the other school**, so the import cannot be completed yet.

This distinction is a core business rule and must be preserved in the automation.

## 294.1 Import Outcome Matrix

```text
                    IMPORT ATTEMPT
                          │
             ┌────────────┴────────────┐
             │                         │
       STUDENT IN                 STUDENT ACTIVE
       OTHER SCHOOL'S             IN OTHER SCHOOL
       DROPBOX                    │
             │                    │
             ▼                    ▼
      IMPORT SUCCESSFUL      IMPORT UNSUCCESSFUL
             │               / IMPORT PENDING
             │                    │
             ▼                    ▼
       GREEN THE ROW          LIGHT ORANGE ROW
       WRITE UID + PEN        REMARK =
       REMARK =               "IMPORT PENDING"
       "IMPORT SUCCESSFULL"   UPDATE IMPORT SHEETS
```

The same outcome model applies to the UDISE and PEN import processes, subject to the exact portal-specific mechanics still being documented from the dedicated import recordings.

---

# 295. IMPORT SUCCESSFUL — REQUIRED FINAL STATE

When the student is successfully imported because the student is found in the **Dropbox of the other school**, the automation must treat the Import operation as successful.

The successful Import state requires all applicable resulting identifiers to be written back to the appropriate spreadsheet record.

## 295.1 Required actions

After verified successful Import:

1. Confirm that the Import actually succeeded in the government portal.
2. Obtain/read the resulting **UID/UDISE** where applicable.
3. Obtain/read the resulting **PEN** where applicable.
4. Write the resulting UID and PEN into the appropriate student spreadsheet record(s).
5. Update the applicable remark to:

```text
IMPORT SUCCESSFULL
```

6. Turn the applicable student row **GREEN**.
7. Persist the completed state so the student is not unnecessarily reprocessed.

## 295.2 Important distinction

GREEN in this situation means:

> **The Import operation has been successfully verified and the resulting student identifiers have been recorded.**

It does NOT merely mean that the Import button was clicked.

The automation must verify the actual successful outcome before changing the row to GREEN.

## 295.3 Required successful state

Conceptually:

```text
Student found in other school's Dropbox
        ↓
Import action performed
        ↓
Portal confirms Import success
        ↓
UID obtained/confirmed
        ↓
PEN obtained/confirmed
        ↓
Spreadsheet UID updated
        ↓
Spreadsheet PEN updated
        ↓
Remark = IMPORT SUCCESSFULL
        ↓
Entire applicable row = GREEN
        ↓
Completed / do not reprocess by default
```

**Resolved for the ACTIVE/pending outcome of both UDISE Import (spec §X)
and PEN Import** ("PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED
WORKFLOW" at the end of this document) — both are DOCUMENTED FROM
RECORDING at click level. This statement still applies, unresolved, to
the **successful/Dropbox outcome** of either portal's Import — no
recording demonstrates it; do not invent it.

---

# 296. IMPORT UNSUCCESSFUL — STUDENT STILL ACTIVE IN OTHER SCHOOL

The second Import outcome occurs when the student is **ACTIVE in the other school**.

In this condition, the Import cannot be completed successfully at the current attempt.

This must NOT be treated as a successful completion.

## 296.1 Required actions

When the portal indicates that the student remains ACTIVE in the other school:

1. Do NOT mark the student GREEN.
2. Do NOT falsely record the Import as successful.
3. Mark the applicable row **LIGHT ORANGE**.
4. Set the remark to:

```text
IMPORT PENDING
```

5. Update the relevant **Import sheet(s)** so the pending Import is explicitly recorded.
6. Preserve enough information to retry/reconcile the Import later.
7. Do not repeatedly attempt the same unsuccessful Import blindly in the same run.

## 296.2 Required pending state

Conceptually:

```text
Student searched/matched
        ↓
Portal shows student ACTIVE in other school
        ↓
Import cannot complete
        ↓
IMPORT SUCCESS = NO
        ↓
Row = LIGHT ORANGE
        ↓
Remark = IMPORT PENDING
        ↓
Import sheet(s) updated
        ↓
Student retained for later reconciliation/retry
```

## 296.3 Meaning of LIGHT ORANGE

LIGHT ORANGE is an **operational pending state**, not a success state and not necessarily a permanent failure.

It indicates:

> The student could not be imported because the student is still active in the other school, and the case requires later follow-up/retry after the source-school status changes.

The automation must therefore distinguish:

```text
GREEN
= verified Import success

LIGHT ORANGE
= Import pending because student is still ACTIVE elsewhere
```

---

# 297. IMPORT SHEET UPDATE REQUIREMENT

The Import-pending condition has a spreadsheet-side consequence in addition to changing the student row color/remark.

When Import remains pending because the student is ACTIVE in another school:

```text
Government portal
      ↓
Student ACTIVE in other school
      ↓
Import unsuccessful
      ↓
Student row = LIGHT ORANGE
      ↓
Remark = IMPORT PENDING
      ↓
Relevant IMPORT sheet(s) updated
```

The Import sheet update is part of the workflow and must not be omitted from the automation design.

The exact columns/values to update must follow the established Import-sheet structure and the dedicated Import recordings. Do not invent additional fields.

---

# 298. UDISE IMPORT — TWO OUTCOME STATES

The UDISE Import workflow therefore has at least these two business outcomes:

## Outcome A — UDISE Import Successful

```text
Student is in other school's Dropbox
        ↓
UDISE Import succeeds
        ↓
UID/UDISE obtained or confirmed
        ↓
PEN obtained/confirmed where available through the Import result/workflow
        ↓
Relevant spreadsheet identifiers updated
        ↓
Remark = IMPORT SUCCESSFULL
        ↓
UDISE row = GREEN
```

The exact relationship between UDISE Import success and the PEN value must follow the actual portal result and dedicated recording. The automation must not manufacture a PEN if the portal does not provide one.

## Outcome B — UDISE Import Unsuccessful / Pending

```text
Student is ACTIVE in other school
        ↓
UDISE Import cannot complete
        ↓
UDISE row = LIGHT ORANGE
        ↓
Remark = IMPORT PENDING
        ↓
Relevant Import sheet updated
        ↓
Retry/reconciliation later
```

---

# 299. PEN IMPORT — TWO OUTCOME STATES

The PEN Import workflow follows the same business distinction:

## Outcome A — PEN Import Successful

```text
Student is in other school's Dropbox
        ↓
PEN Import succeeds
        ↓
PEN obtained/confirmed
        ↓
Relevant UID/UDISE also recorded where the successful result provides it
        ↓
Remark = IMPORT SUCCESSFULL
        ↓
PEN row = GREEN
```

Again, the exact portal mechanics and which identifier is returned at each stage must be taken from the dedicated PEN Import / Other State recording.

## Outcome B — PEN Import Unsuccessful / Pending

```text
Student is ACTIVE in other school
        ↓
PEN Import cannot complete
        ↓
PEN row = LIGHT ORANGE
        ↓
Remark = IMPORT PENDING
        ↓
Relevant Import sheet(s) updated
        ↓
Retry/reconciliation later
```

---

# 300. IMPORT SUCCESS VS IMPORT PENDING — AUTOMATION RULES

The automation must use an explicit outcome classifier rather than assuming success after an Import action.

```text
IMPORT_ATTEMPT
      ↓
READ PORTAL RESULT
      ↓
┌───────────────────────────────┐
│ Is student successfully       │
│ imported from other school's  │
│ Dropbox?                      │
└───────────────┬───────────────┘
                │
        ┌───────┴───────┐
        │ YES           │ NO
        ▼               ▼
IMPORT SUCCESS      CHECK REASON
        │               │
        │               ▼
        │       Student ACTIVE
        │       in other school?
        │               │
        │          ┌────┴────┐
        │          │ YES     │ NO/UNKNOWN
        │          ▼         ▼
        │     IMPORT       MANUAL
        │     PENDING      REVIEW / ERROR
        │          │
        ▼          ▼
GREEN        LIGHT ORANGE
UID/PEN      IMPORT PENDING
UPDATED      IMPORT SHEET UPDATED
REMARK       RETRY LATER
SUCCESSFULL
```

If the portal result is ambiguous, the automation must NOT choose either success or pending arbitrarily. It must enter a manual-review/error state until the actual outcome can be verified.

---

# 301. IMPORT ROW-COLOR SEMANTICS

The project now has three important row-state categories relevant to Import:

| State | Meaning | Remark | Processing behavior |
|---|---|---|---|
| GREEN | Import successfully verified | `IMPORT SUCCESSFULL` | Completed; skip by default |
| LIGHT ORANGE | Import could not complete because student is ACTIVE in other school | `IMPORT PENDING` | Keep for later retry/reconciliation |
| Other / unchanged | Not yet processed or another workflow state | Depends on condition | Follow applicable workflow |

These colors are workflow-state indicators and must not be confused with portal status labels.

---

# 302. IMPORT PENDING IS NOT THE SAME AS PEN = ND

This distinction is mandatory.

`PEN = ND` means that the PEN is **Not Defined / Not Available** in the relevant completed New PEN workflow state and can legitimately coexist with a GREEN PEN row.

`IMPORT PENDING` means that an Import operation **did not complete because the student is still ACTIVE in another school** and requires later action.

Therefore:

```text
PEN = ND + GREEN
        ≠
IMPORT PENDING + LIGHT ORANGE
```

They represent completely different workflow states.

---

# FINAL AUTHORITY — FINAL SPECIFICATION

This section supersedes any earlier contradictory statement in this document. It exists because later videos and later conversation decisions expanded and corrected the earlier handoff.

## A. COMPLETE SOURCE INVENTORY

The project source recordings currently present are:

1. `GOOGLE SHEET.mp4` — approximately 1:55
2. `GUJARAT ENTRY.mp4` — approximately 10:44
3. `AFTER UDISE ENTRY BEFORE PEN .mp4` — approximately 2:03
4. `PEN ENTRY.mp4` — approximately 6:15
5. `5 ND MANUAL UPDATE.mp4` — approximately 1:52
6. `UDISE IMPORT (OTHER SCHOOL ACTIVE).mp4` — approximately 1:28
7. `PEN IMPORT (OTHER SCHOOL ACTIVE).mp4` — approximately 3:55
8. `PEN REQUEST SENT .mp4` — approximately 1:36
9. `HOW TO VIEW SENT REQUEST.mp4` — approximately 0:15

The later three recordings are not optional context. They extend the original workflow specification and must be incorporated.

The source recordings establish observed UI/process evidence. The conversation establishes business rules that may not be visible in every recording. Both sources must be preserved, but they must never be conflated: video-observed behavior is video evidence; a business rule explicitly stated by the user is a project requirement; an implementation inference must be labeled as an inference and must not be presented as an observed portal fact.

## B. NON-NEGOTIABLE UI-CHANGE RESILIENCE REQUIREMENT

Government portals are complex, stateful applications and their UI may change slightly after this specification is written. The automation MUST therefore be designed as a resilient state-aware browser automation system rather than a recorded click macro.

Never depend on:

- fixed screen coordinates;
- absolute mouse positions;
- image locations alone;
- a single brittle CSS selector;
- a single generated DOM class name;
- a single exact text string where normalization/aliases are possible;
- timing assumptions such as "wait 2 seconds then click";
- a fixed number of DOM elements;
- a fixed visual layout;
- browser zoom or window size as a business dependency.

Prefer, in order:

1. accessible role/name;
2. associated label and input relationship;
3. stable element ID/name;
4. stable data attributes;
5. semantic text plus surrounding DOM context;
6. table header/column relationships;
7. student identity matching across visible row fields;
8. URL/route/title/state markers;
9. a controlled set of fallback selectors;
10. visual evidence only when necessary and always followed by state verification.

Selectors must be centralized in portal adapters/page objects rather than scattered throughout workflow code.

Each important portal control should support multiple candidate selectors or discovery strategies where practical. Selector candidates must be attempted deterministically and their result recorded in diagnostics.

## C. UI CHANGE CLASSIFICATION

The automation must classify unexpected UI differences before acting.

### C1. Harmless presentation change
Examples:

- button moved;
- spacing changed;
- a panel is collapsed;
- table width changed;
- non-business-critical CSS changed.

The automation may adapt automatically if the semantic target can still be identified and the expected state can be verified.

### C2. Semantic-equivalent control change
Examples:

- `Save Student` becomes `Save`;
- `Next` moves to a different container;
- a search field receives a different stable ID;
- a portal uses an equivalent label.

The adapter may use controlled aliases/fallback discovery.

### C3. New known confirmation/intermediate step
If the new screen corresponds to an already-known business action and can be safely identified, handle it through a versioned adapter rule and verify the resulting state.

### C4. Unknown business state
If the portal presents an unexpected warning, confirmation, student identity, transfer state, request state, or action whose business meaning is not established by the specification, DO NOT GUESS.

Pause safely, capture diagnostics, preserve the last verified state, and request manual intervention.

## D. CONSEQUENTIAL ACTION RULE

For every consequential operation:

DISCOVER → IDENTIFY → VERIFY → ACT → VERIFY RESULT → RECORD EVENT → UPDATE SHEET ONLY WHEN ALLOWED.

Examples of consequential actions include:

- student creation;
- transfer request submission;
- profile save;
- update transfer request;
- Aadhaar consent/verification action;
- completion action;
- spreadsheet status/color change to GREEN;
- replacing ND with an actual PEN;
- any action that changes government portal state.

The automation must never use:

ACT → ASSUME SUCCESS → UPDATE SHEET.

## E. STUDENT IDENTITY VERIFICATION

Before any consequential action, verify enough independent student attributes to prevent operating on the wrong record.

Where available, use a combination such as:

- student name;
- father name;
- mother name;
- surname;
- DOB;
- UID/UDISE;
- PEN;
- class;
- GR/admission number;
- school context.

A single name match is insufficient where multiple records can exist.

If identity is ambiguous, stop for manual review.

## F. STATE VERIFICATION

Every workflow must maintain an explicit last-known-verified state.

Examples:

- spreadsheet state before action;
- portal page/state before action;
- request existence;
- request status;
- profile completion state;
- actual PEN/NA state;
- UDISE UID state.

If an action may have succeeded but the browser lost the response, NEVER repeat the consequential action blindly. Re-open or inspect the relevant portal state first.

## G. RETRY SAFETY

Retry only when the failure is known to be retryable.

Retryable examples:

- network timeout before action execution;
- transient page-load failure;
- known recoverable navigation failure.

Potentially non-idempotent actions require verification before retry:

- transfer request submission;
- profile save;
- student initialization;
- request creation;
- any action whose duplicate could create a second request/record.

If the system cannot determine whether the first attempt succeeded, enter VERIFYING rather than immediately retrying.

## H. FULL ERROR DIAGNOSTICS

On an unexpected portal state, save as much as safely available:

- timestamp;
- student ID;
- student name snapshot;
- workflow;
- current state;
- URL;
- page title;
- visible relevant text;
- screenshot;
- attempted selector/discovery strategy;
- expected element/state;
- observed element/state;
- error code;
- exception message;
- attempt number;
- browser/session identifier;
- automation build/version;
- last verified state;
- whether retry is permitted.

Never report merely `Element not found`.

## I. CAPTCHA / OTP / SECURITY / AADHAAR CONSENT

CAPTCHA is a manual security boundary unless an officially authorized mechanism is explicitly provided and the user authorizes its use.

Do not attempt to defeat, solve around, bypass, or automate CAPTCHA.

OTP/MFA must remain manual unless an official supported automation mechanism is explicitly available and authorized.

Aadhaar demographic-authentication consent such as `CONSENT FOR DEMOGRAPHIC AUTHENTICATION` and `I Agree` is a controlled human-intervention point unless the user explicitly authorizes automation of that exact action and the implementation can do so in a compliant manner.

The system should pause, clearly tell the operator what is required, then resume from the saved checkpoint.

## J. SPREADSHEET INTEGRITY RULES

Spreadsheet state is evidence of the application's recorded business state, not a substitute for portal verification.

Never mark a row GREEN solely because:

- a form was filled;
- a Save button was clicked;
- a page navigated;
- an HTTP request returned without an observed business-success state;
- a student appeared in a list without verifying the required completion condition.

UDISE success means the entire UDISE row becomes GREEN only after the required UDISE workflow is verified complete.

PEN success means the entire PEN row becomes GREEN only after the required PEN workflow is verified complete, including valid `ND` where the portal has not yet assigned an actual PEN.

OGR row color must remain unchanged during government-entry completion unless a separately specified OGR update operation explicitly authorizes a change.

## K. IMPORT / REQUEST TERMINOLOGY

Do not replace the user's established terminology with generic terms.

For an active other-school transfer request, the spreadsheet remark is:

`REQUEST SENT`

The corresponding spreadsheet visual state is:

`LIGHT ORANGE`

Do not rename this business state to `IMPORT PENDING` merely because an import is expected later.

The workbook may contain an `IMPORT PENDING` tab/structure for operational records, but that does not redefine the active request remark.

`REQUEST SENT` means the transfer/request process has been initiated and is not the same thing as successful import/completion.

## L. WITHIN-STATE / OUTSIDE-STATE RULE

Within State:

`Gujarat → Gujarat`

Outside State:

`Other State → Gujarat`

For the PEN request/approval business process, the user explicitly requires the same business approach for both. Do not create separate business logic solely because the source state differs.

Portal-specific routing may differ if the actual portal requires it, but the business-state model, request monitoring, reporting, and manual-review rules must remain unified.

## M. APPROVAL CHECK — BATCHED CONFIRMATION

When automation is ready to check students whose spreadsheet state is LIGHT ORANGE / REQUEST SENT, it must ask for permission ONCE for the complete batch.

Do not ask once per student.

After permission:

1. collect all applicable LIGHT ORANGE students;
2. check their current portal status one by one;
3. record the current status for every student in the application database;
4. preserve the spreadsheet state unless an explicitly authorized update is allowed;
5. continue checking remaining students even when one has a changed status or a technical failure;
6. produce one combined report.

The report must separate:

### Still Pending
Students whose portal status remains `Pending at Destination` or equivalent exact current portal wording.

### Status Changed
Students whose current portal status differs from the previous recorded portal status.

The exact portal status text must be preserved.

If every checked student remains pending, the final message must be:

`All transfer requests are still pending and no action is required.`

## N. STATUS-CHANGED MANUAL REVIEW

A status change does NOT authorize automatic further action.

For a status-changed student, show:

- student name;
- UID/UDISE;
- PEN if available;
- request ID if available;
- previous portal status;
- current portal status;
- current spreadsheet status;
- current spreadsheet color;
- date/time checked;
- performed by.

The application must notify separately that manual review may be required.

`View Details` must show the complete status history and relevant request details.

`Take Next Action` must open the student's relevant Status Page so the operator can perform the action manually first.

After manual action, require a short action description before `Mark Action Completed` is accepted.

The student remains in the Status Changed manual-review list until the user explicitly closes/resolves the case.

Resolution requires a resolution note.

Reopening must preserve the original resolution history and create a new case cycle; historical events are never overwritten.

## O. APPROVAL HISTORY FILTERING / EXPORT

Approval History must support simultaneous filters:

- Student Name
- UID
- PEN
- Request ID
- Date
- Portal Status
- Performed By (`AUTOMATION` / `MANUAL`)

Provide:

- Search box;
- multiple simultaneous filters;
- Clear/Reset Filters;
- export current filtered results to Excel/XLSX;
- export current filtered results to CSV.

The export must respect the active filters exactly.

## P. PEN CASE EVENT MODEL

The `pen_case_events` table is append-only and immutable.

Required fields:

- `event_id` TEXT PRIMARY KEY, UUID
- `case_id` TEXT NOT NULL
- `case_cycle_id` TEXT NOT NULL, UUID
- `student_id` TEXT NOT NULL
- `student_name` TEXT NOT NULL snapshot
- `pen` TEXT nullable; valid 11-digit PEN or `ND`
- `uid_udise` TEXT nullable
- `workflow` TEXT NOT NULL
- `event_code` TEXT NOT NULL
- `event_version` INTEGER NOT NULL positive
- `previous_event_id` TEXT nullable except first event
- `case_status_before` TEXT NOT NULL
- `case_status_after` TEXT NOT NULL
- `portal_status` TEXT nullable
- `portal_status_previous` TEXT nullable
- `spreadsheet_status` TEXT NOT NULL snapshot
- `spreadsheet_color` TEXT NOT NULL snapshot
- `action_description` TEXT nullable; mandatory for manual-action events
- `resolution_note` TEXT nullable; mandatory for resolution/closure
- `reopen_reason` TEXT nullable; mandatory for reopen
- `error_code` TEXT nullable; mandatory for failure
- `error_message` TEXT nullable; mandatory for failure
- `attempt_number` INTEGER nullable; positive for retry events
- `authorized_by` TEXT nullable; mandatory for consequential user authorization
- `performed_by` TEXT NOT NULL: `AUTOMATION` or `MANUAL`
- `occurred_at` TEXT NOT NULL ISO-8601 timezone-aware
- `created_at` TEXT NOT NULL
- `metadata_json` TEXT nullable, valid JSON
- recommended `event_hash`
- recommended `previous_event_hash`

The event chain should be tamper-evident where practical.

## Q. CONTROLLED PEN CASE STATUSES

Allowed case statuses:

- `ACTION_REQUIRED`
- `RETRYING`
- `VERIFYING`
- `MANUAL_REVIEW`
- `RESOLVED`
- `UNRESOLVED_CLOSED`
- `REOPENED`

Allowed performers:

- `AUTOMATION`
- `MANUAL`

## R. CONTROLLED PEN EVENT CODES

At minimum:

- `PEN_ACTION_REQUIRED_OPENED`
- `PEN_RETRY_STARTED`
- `PEN_RETRY_FAILED`
- `PEN_VERIFICATION_STARTED`
- `PEN_VERIFICATION_RESULT`
- `PEN_UNRESOLVED`
- `PEN_MANUAL_ACTION_STARTED`
- `PEN_MANUAL_ACTION_COMPLETED`
- `PEN_RESOLUTION_STARTED`
- `PEN_RESOLVED`
- `PEN_SPREADSHEET_UPDATE_AUTHORIZED`
- `PEN_SPREADSHEET_UPDATE_COMPLETED`
- `PEN_SPREADSHEET_UPDATE_FAILED`
- `PEN_CASE_REOPENED`
- `PEN_REOPEN_VERIFICATION`
- `PEN_REOPENED_ACTION_REQUIRED`
- `PEN_UNRESOLVED_CLOSED`
- `PEN_CASE_REOPENED_AFTER_UNRESOLVED`
- `PEN_INVALID_TRANSITION_ATTEMPT`

Invalid transitions must be rejected and logged as `PEN_INVALID_TRANSITION_ATTEMPT`.

## S. PEN CASE TRANSITIONS

At minimum:

`ACTION_REQUIRED → RETRYING`

`ACTION_REQUIRED → VERIFYING`

`ACTION_REQUIRED → MANUAL_REVIEW`

`RETRYING → ACTION_REQUIRED` after failure

`RETRYING → VERIFYING` when verification is required

`VERIFYING → result-derived state`

`MANUAL_REVIEW → manual action / resolution path`

`RESOLVED → REOPENED` only

`UNRESOLVED_CLOSED → REOPENED` only

`REOPENED → VERIFYING / ACTION_REQUIRED / MANUAL_REVIEW`

Consequential resolution requires manual authorization and a resolution note plus the final verified portal state where applicable.

Unresolved closure is not the same as resolved.

A reopen creates a new `case_cycle_id`; previous history remains immutable.

## T. TECHNICAL FAILURE VS BUSINESS STATE

A technical failure must never silently become a business status.

Examples:

### Timeout/network/DOM failure
Preserve last verified state. No spreadsheet business-state change. Record technical error.

### Click may have succeeded but confirmation was lost
Verify current portal state before repeating the click.

### Session expiry
Pause. Require the operator to complete login/security requirements. Resume from checkpoint.

### Browser crash
Persist DB state. Reopen session. Verify before repeating consequential actions.

### One student failure
Do not stop the entire safe batch unless continuing would risk incorrect state. Isolate the student, record failure, continue other independent students.

### Status-check failure
Keep spreadsheet `LIGHT ORANGE / REQUEST SENT`; record failure; continue other students.

### Portal outage
Stop affected operations safely. Do not modify spreadsheet status. Record checked and unchecked students.

### Spreadsheet write failure after portal success
Preserve portal success in DB. Record spreadsheet failure. Do not repeat the portal operation. Provide a spreadsheet-only recovery path.

### Database failure
Do not claim an event was recorded. Stop consequential operation safely.

### Unknown portal state
Stop, capture screenshot/URL/title/expected-vs-observed state, and require manual intervention.

## U. IDENTITY / VALUE RULES

`UID` and `UDISE` refer to the same identifier in this project context.

UDISE/UID is treated as an 18-digit value by the project.

PEN is an 11-digit identifier when actually assigned.

National portal may show `NA` when PEN is not available.

School spreadsheet uses `ND` = Not Defined.

Mapping:

`Portal NA → Spreadsheet ND`

Do not:

- invent a temporary PEN;
- copy the school UDISE code into PEN;
- use UID as PEN;
- create a fake 11-digit value.

## V. ND RECONCILIATION

For a student whose completed PEN spreadsheet value is `ND`:

1. open the National UDISE+ Student Database;
2. select the correct class FIRST;
3. search by student name;
4. match the correct student;
5. read the current PEN value.

If an actual 11-digit PEN exists:

- replace `ND` in PEN sheet with the actual PEN;
- update OGR PEN;
- preserve audit history.

If the portal still has no actual PEN / shows NA:

- keep spreadsheet `ND`;
- do not invent a value.

Observed portal list can show:

- class/grade;
- PEN;
- student name;
- gender;
- DOB;
- entry status;
- last updated;
- GP/EP/FP indicators;
- profile/document icon.

Observed portal statuses include `Not Started`, `In-Progress`, and `Completed`.

## W. UDISE NEW ENTRY — AUTHORITATIVE OBSERVATIONS

The Gujarat Child Tracking System / Gujarat UDISE workflow includes:

- login with school code/username;
- password;
- CAPTCHA;
- LOG IN;
- visible school code example `24224100067`;
- Home and student-management navigation;
- Manage Students;
- Standard Wise Entry;
- Student New Entry;
- CRS-RGI route;
- Manual birth-data route;
- Manage Students student list;
- Personal/Education/Bank/Scholarship & Facility/Health & CWSN profile areas;
- final SAVE STUDENT behavior.

CRS-RGI observed fields include:

- BRN;
- Birth Year;
- Birth Month;
- Birth Date;
- Gender;
- `GET DETAILS FROM CRS-RGI`.

Manual birth route observed fields include:

- Birth State;
- Birth District;
- Birth Taluka;
- Birth City/Place;
- Birth Village;
- Year;
- Month;
- Date;
- BRN;
- Birth Certificate No.;
- PDF upload;
- Next.

Example observed manual values included Odisha / Ganjam / Sheragada and a January 2022 birth record. These are examples only and must not be hardcoded.

Student profile observed information includes:

- Student name;
- Father name;
- Mother name;
- Surname;
- DOB;
- disability yes/no;
- disability type;
- guardian information;
- address;
- district/block/locality;
- mother tongue;
- category;
- religion.

Education observed information includes:

- admission number;
- date of admission;
- class;
- RTE;
- previous academic status/result;
- percentage;
- attendance;
- medium/language/subjects;
- mandatory/general subjects;
- additional subjects;
- co-curricular subjects.

Bank information must never be filled with fabricated values merely to satisfy a form. Use actual data, explicit NA/blank options where the portal permits, or manual intervention when the portal requires a value not supported by the source data.

Scholarship & Facility and Health & CWSN field numbering/details were not completely machine-readable in every frame; use live DOM verification and do not invent exact labels not established by the evidence.

Final UDISE completion requires the required profile completion, not merely creation of a UID.

## X. UDISE ACTIVE / TRANSFER REQUEST OBSERVATIONS

Observed Gujarat Child Tracking System ACTIVE workflow:

1. Log in.
2. Open Manage Students → Standard Wise Entry.
3. Select class.
4. Search by UID/UDISE.
5. Existing student can be found at another school.
6. Portal asks for transfer-request confirmation.
7. Confirm.
8. Transfer Student page displays source student information.
9. Transfer From displays source district/block/school/principal details.
10. Transfer To displays destination cluster/school/class context.
11. Use `Update Transfer Request`.
12. Success message observed:
   `Student Transfer request saved successfully.`
13. This means the request was submitted; it does NOT mean import/completion has occurred.
14. Student Transfer Request List contains:
   - Sent Transfer Requests;
   - Received Transfer Requests;
   - Completed Transfer Requests;
   - pending/status filtering.
15. Spreadsheet state becomes:
   - `REMARK = REQUEST SENT`
   - `LIGHT ORANGE` row/state according to the project business rule.

The observed example was AARUSHI, Class 1, UID `242215284482520014`, existing at SHREE KRUSHNARAJ VIDYALAY (ENG MED), with destination SATYAM STARS INTERNATIONAL... The example values are evidence of field behavior, not hardcoded application data.

## Y. PEN NEW ENTRY — AUTHORITATIVE OBSERVATIONS

National UDISE+ / PEN workflow observed:

1. Open configured/current UDISE+ portal URL.
2. Operate within school context.
3. Initialize/save new student profile.
4. Success modal observed:
   `The Student has been initialised/Saved Successfully.`
5. Modal includes student name/class/section and actions such as Add New Student, Go to New Entry List, Fill General Profile.
6. Student profile stages include:
   - General Profile;
   - Enrolment Profile;
   - Facility Profile;
   - Profile Preview.
7. Header can show:
   - Permanent Education Number — Not Defined;
   - Student AADHAAR Verified;
   - CWSN;
   - Impairment Type.
8. General Profile includes guardian, Aadhaar, name as per Aadhaar, admission date, mobile numbers, CWSN, address, pincode, email, mother tongue, social category, religion, BPL/AAY/EWS/disadvantaged indicators.
9. Aadhaar demographic authentication consent dialog is observed.
10. Enrolment Profile includes admission number/date, class/roll, medium, languages, subjects, previous academic status, RTE, previous result, percentage, attendance.
11. Facility Profile includes competition/olympiad, NCC/NSS/Scouts & Guides, height, weight, distance to school, highest education level of parent/guardian, then Save/Next.
12. Final success modal:
    `Data completion is complete.`
13. Return to student dashboard.
14. PEN sheet is updated to `ND` when the portal has not assigned an actual PEN.
15. Entire PEN row becomes GREEN.

`PEN=ND + GREEN` is therefore a valid completed New PEN state.

## Z. CLASS ROUTING

The class routing rule applies to both UDISE and PEN workflows:

JrKG / SrKG / Balvatika / 1st → Satyam School ID workflow.

2nd onward → Block ID workflow.

The application must make routing data-driven and configurable rather than hardcoding scattered if/else statements throughout the code.

## AA. FOUR WORKFLOW CONDITIONS

The application must support these four conditions:

1. New UDISE + New PEN
2. New UDISE + PEN Import / request-based existing-student path
3. UDISE already available/imported + New PEN
4. UDISE + PEN both imported

Do not collapse the four conditions into one generic New Entry workflow.

Do not assume that Import is simply New Entry with fewer fields.

## AB. PHASES

PH1, PH2, PH3 are operational batches/phases, not different database structures.

They represent when required student documents/data became ready.

Do not create separate schemas merely because a student belongs to PH1, PH2, or PH3.

## AC. EXACT WORKBOOK STRUCTURES

### UDISE_Entry_(State).xlsx

Tabs:

- PH1
- PH2
- PH3

Main headers:

1. REMARK
2. Class
3. UDISE No
4. Birth Cert Reg No
5. Birth Year
6. Birth Month
7. Birth Date
8. Gender
9. Birth State
10. Birth District
11. Birth City
12. Student Name
13. Father's Name
14. Mother's Name
15. Surname
16. Date of Birth
17. GR No
18. Roll No
19. Plot Number
20. Society
21. Landmark
22. Area
23. Pin Code
24. Mother Tongue
25. Date of Join
26. Aadhar Card No
27. Name as per Aadhar
28. Mobile No 1
29. Mobile No 2

PH3 may contain an additional blank/unused column. Do not treat an unused column as a business field without evidence.

### PEN_Entry_(National).xlsx

Main tabs include:

- PH1
- PH2
- PH3
- IMPORT PENDING

Main PEN headers:

1. PEN
2. Class
3. Student Father Surname
4. Gender
5. Date of Birth
6. Student State Code (UDISE No)
7. Mother's Name
8. Father's Name
9. Aadhar Number of Student
10. Name of Student as per Aadhar Card
11. Admission Date
12. Full Address
13. Pincode
14. Mobile No 1
15. Mobile No 2
16. Mother Tongue
17. Admission Number in Present School (GR No)
18. Roll No
19. Previous Class Percentage
20. Previous Class Attendance Days
21. Height (cm)
22. Weight (kg)

IMPORT PENDING headers observed:

- SR NO
- STUDENT NAME
- PEN
- DOB
- SCHOOL NAME
- SCHOOL UDISE
- STATE
- DISTRICT
- BLOCK
- HEADMASTER
- CONTACT NO
- STATUS
- REMARK

## AD. GOOGLE SHEETS REQUIREMENT

The application must support Google Sheets as an operational source/sink where configured.

Use the official Google Sheets API and proper authentication. Do not scrape Google Sheets through the browser when the API is available.

Google credentials/secrets must never be hardcoded.

The desktop application remains local. Google Cloud is used only for official API authentication/configuration as required, not as the application's hosting environment.

## AE. LOCAL APPLICATION STACK

Required target stack:

- Python
- PySide6
- Playwright
- SQLite
- Google Sheets API
- openpyxl
- PyInstaller

The application is a Windows desktop application.

Browser automation must use a real headed/visible browser for the government portal unless an explicitly authorized workflow proves that headless operation is safe and useful. CAPTCHA/security steps require visibility.

## AF. APPLICATION DATABASE ROLE

SQLite is the application's workflow/audit database.

It is NOT the OGR.

It stores:

- normalized student identity/reference;
- spreadsheet source metadata;
- workflow condition;
- portal state;
- job/run state;
- checkpoints;
- retries;
- errors;
- screenshots/diagnostics references;
- approval history;
- PEN case state;
- immutable PEN events;
- manual interventions;
- authorization records;
- resolution/reopen history.

## AG. GREEN ROW SKIP RULE

A row that is already GREEN and whose required workflow is verified complete should be skipped by default.

Never blindly reprocess GREEN rows.

The UI may provide an explicit operator-authorized recheck/reconciliation action where safe, but ordinary batch processing must skip completed rows.

## AH. FUTURE/COMING-SOON BOUNDARIES

The coding agent must implement everything that is fully specified and observed.

It must NOT invent:

- undocumented government import-success mechanics;
- undocumented approval actions;
- undocumented portal API endpoints;
- undocumented selectors presented as facts;
- undocumented field meanings;
- fake success states;
- automatic handling of unknown government UI states.

Where an exact government behavior remains unobserved, implement an explicit adapter boundary and mark that workflow as `COMING_SOON` or `MANUAL_REQUIRED` rather than guessing.

Future video uploads can extend the adapter/workflow implementation. New video evidence must be treated as authoritative for the specific previously undocumented behavior it demonstrates, while preserving all existing business rules unless the user explicitly changes them.

## AI CODING AGENT OPERATING INSTRUCTIONS

The coding agent receiving this specification must behave as a senior engineer owning the implementation.

It must:

1. Inspect the repository before changing anything.
2. Inspect existing source files, tests, configuration, database migrations, and documentation.
3. Build a project implementation checklist.
4. Convert every requirement in this specification into a tracked engineering task.
5. Identify which tasks are implemented, partially implemented, blocked by missing portal evidence, or intentionally manual.
6. Build the local application foundation before adding complex portal automation.
7. Implement data models and state machines before consequential browser actions.
8. Implement portal adapters/page objects rather than a monolithic automation script.
9. Add structured logging and persistent checkpoints.
10. Add screenshots/diagnostics around failures.
11. Add deterministic retry/recovery behavior.
12. Add unit tests for mapping, state transitions, validation, and idempotency.
13. Add browser-level tests using mocked/stubbed portal pages where live government automation cannot safely be tested.
14. Add dry-run/simulation support where useful without pretending that simulation equals government success.
15. Never hardcode government credentials.
16. Never bypass CAPTCHA or security controls.
17. Never silently change spreadsheet business state after an unverified portal action.
18. Never mark GREEN without the defined completion verification.
19. Never duplicate a transfer request because a confirmation response was lost.
20. Never replace ND with a fabricated PEN.
21. Never convert a technical failure into a business success/failure state without explicit rules.
22. Continue independent batch records when one student safely fails.
23. Stop when continuing would risk incorrect government data.
24. Ask the human only when an actual unobserved/ambiguous government behavior is required; do not ask questions already answered by this specification.
25. Make reasonable internal engineering decisions autonomously.
26. Keep all decisions documented in code/comments/architecture notes where they affect future maintenance.
27. At the end of implementation, produce a checklist showing every requirement and its implementation status.
28. Explicitly document anything that remains manual or Coming Soon and why.

## UI CHANGE HANDLING — IMPLEMENTATION ACCEPTANCE TESTS

The implementation is not accepted merely because it works against today's exact screenshots.

Acceptance tests must include simulated UI changes such as:

- changed button location;
- changed CSS class;
- changed stable/non-stable element ID;
- equivalent button label;
- additional wrapper `<div>`;
- reordered form fields;
- table columns moved;
- extra confirmation modal;
- pagination/control position changed;
- minor text punctuation/capitalization changes.

For known semantic-equivalent changes, the automation should continue and verify the state.

For unknown business changes, it must stop safely and generate diagnostics.

## FINAL COMPLETION STANDARD

The project is complete only when:

- all currently specified data structures are supported;
- all four workflow conditions are represented;
- New UDISE is implemented to the observed workflow;
- UDISE ACTIVE request/import workflow is represented from the dedicated evidence;
- New PEN is implemented to the observed workflow;
- PEN OTHER SCHOOL ACTIVE request/import workflow is represented from the dedicated evidence;
- PEN REQUEST SENT monitoring is represented;
- HOW TO VIEW SENT REQUEST behavior is represented;
- ND reconciliation is implemented;
- approval monitoring and history are implemented;
- immutable PEN event history is implemented;
- retry/recovery/idempotency rules are implemented;
- manual intervention points are implemented;
- spreadsheet update rules are enforced;
- UI-change resilience is implemented;
- unknown portal states are safely contained;
- tests cover state transitions and failure scenarios;
- the application can resume from a persisted checkpoint;
- no false GREEN or fabricated PEN can be produced.

The final coding agent must treat this entire document as an engineering specification, not as a short summary.


# FINAL RECONCILIATION AND IMPLEMENTATION GATE

## 1. Source inventory — authoritative

| Source | Duration | Role | Status |
|---|---:|---|---|
| `GOOGLE SHEET.mp4` | 115.20 s | School spreadsheet/data workflow | Incorporated |
| `GUJARAT ENTRY.mp4` | 644.00 s | Gujarat UDISE new-entry workflow | Incorporated |
| `AFTER UDISE ENTRY BEFORE PEN .mp4` | 122.60 s | Transition/state between UDISE and PEN | Incorporated |
| `PEN ENTRY.mp4` | 374.95 s | National UDISE+/PEN new-entry workflow | Incorporated |
| `5 ND MANUAL UPDATE.mp4` | 112.05 s | ND reconciliation/manual PEN update | Incorporated |
| `UDISE IMPORT (OTHER SCHOOL ACTIVE).mp4` | 88.53 s | UDISE other-school ACTIVE/import-request workflow | Incorporated |
| `PEN IMPORT (OTHER SCHOOL ACTIVE).mp4` | 234.88 s | PEN other-school ACTIVE/import workflow | Incorporated |
| `PEN REQUEST SENT .mp4` | 96.30 s | PEN request-sent workflow/status | Incorporated |
| `HOW TO VIEW SENT REQUEST.mp4` | 14.70 s | Viewing sent request/status | Incorporated |

## 2. Final business-state distinction

The implementation MUST keep these states distinct even when they use the same LIGHT ORANGE visual color.

### Import workflow

```text
Student ACTIVE in another school
        ↓
Import attempted
        ├── successful import / Dropbox path
        │       ↓
        │   IMPORT SUCCESSFUL
        │       ↓
        │   required identifiers/state verified
        │       ↓
        │   GREEN
        │
        └── student still ACTIVE elsewhere
                ↓
            IMPORT PENDING
                ↓
            LIGHT ORANGE
                ↓
            retain for later retry/reconciliation
```

### Transfer-request workflow

```text
Transfer request submitted
        ↓
REQUEST SENT
        ↓
LIGHT ORANGE
        ↓
Batch approval/status check
        ├── Pending at Destination
        │       ↓
        │   remain REQUEST SENT / LIGHT ORANGE
        │
        └── Status Changed
                ↓
            manual review
                ↓
            authorized next action
```

**Never rename `REQUEST SENT` to `IMPORT PENDING`. Never interpret PEN `ND` as `IMPORT PENDING`. Never interpret LIGHT ORANGE by color alone; the database/workflow status is authoritative.**

## 3. UI-change resilience — mandatory implementation gate

Government portals may change labels, DOM structure, CSS classes, spacing, page layout, confirmation wording, or navigation without changing the underlying business process. The automation MUST therefore use a state-driven adapter architecture.

### Required selector hierarchy

1. Accessible role/name.
2. Associated label/input relationship.
3. Stable `id` / `name`.
4. Stable `data-*` attributes.
5. Semantic text plus DOM context.
6. Table headers and row/column relationships.
7. Student identity matching across multiple visible fields.
8. URL/route/title/state indicators.
9. Controlled fallback discovery.
10. Visual assistance only when unavoidable, never as the sole proof of a consequential action.

### Prohibited

- fixed mouse coordinates as the primary automation method;
- blind recorded click sequences;
- arbitrary `sleep()` calls as the synchronization mechanism;
- one fragile selector for a critical action;
- assuming success because a click completed;
- automatically choosing an unknown option after a UI change.

### Required behavior when UI changes

- Detect whether the page is still the expected logical page.
- Try approved selector candidates.
- Normalize harmless text variations.
- Verify the target student's identity before consequential actions.
- Verify the resulting business state after the action.
- Record which selector strategy succeeded.
- If the change is semantically understood, continue automatically.
- If the page represents an unknown business state, pause safely and require manual intervention.
- Capture screenshot, URL, title, relevant DOM diagnostics, workflow state, attempted selectors, and last verified state.

The system must be **resilient**, not blindly “self-healing.” It may adapt to harmless presentation changes, but it must never invent business meaning.

## 4. Consequential-action verification rule

Every consequential government-portal operation follows:

```text
Locate target
  ↓
Verify student identity
  ↓
Verify current portal state
  ↓
Perform action
  ↓
Wait for state transition
  ↓
Verify expected result
  ↓
Record immutable event/audit entry
  ↓
Only then update spreadsheet workflow state
```

If the result cannot be verified, the automation MUST NOT mark the student successful.

## 5. Final conversation-to-specification coverage checklist

Before implementation is considered complete, the coding agent must verify that the specification has explicit implementation coverage for all of the following:

- school admission/document preparation context;
- PH1/PH2/PH3 batch semantics;
- OGR separation from application database;
- three operational spreadsheet files;
- exact UDISE workbook structure;
- exact PEN workbook structure;
- Import/PEN/UDISE terminology;
- four entry conditions;
- class routing;
- Satyam School ID workflow;
- Block ID workflow;
- UDISE new-entry workflow;
- UDISE complete-profile GREEN rule;
- UDISE other-school ACTIVE workflow;
- transfer-request workflow;
- `REQUEST SENT`;
- LIGHT ORANGE semantics;
- PEN new-entry workflow;
- PEN `ND`;
- PEN GREEN rule;
- ND reconciliation;
- Other School ACTIVE import workflow;
- successful import/Dropbox path;
- Import Pending path;
- PEN request-sent workflow;
- sent-request viewing workflow;
- combined approval monitoring;
- batch confirmation once for all LIGHT ORANGE students;
- approval history;
- filters/search/reset;
- XLSX/CSV export respecting filters;
- Still Pending/Status Changed report separation;
- manual-review notification;
- View Details;
- Take Next Action;
- Mark Action Completed;
- action description requirement;
- resolution note;
- reopen behavior;
- immutable PEN event chain;
- allowed event transitions;
- invalid-transition logging;
- error/retry/recovery rules;
- idempotency;
- session expiry;
- browser crash recovery;
- portal outage handling;
- spreadsheet-write failure after portal success;
- database failure safety;
- unknown portal state;
- CAPTCHA/manual security boundaries;
- Aadhaar consent boundary;
- screenshots/diagnostics;
- checkpoints/resume;
- UI-change resilience;
- selector fallback strategy;
- state verification;
- tests;
- autonomous implementation checklist;
- Coming Soon/manual boundaries;
- no false GREEN;
- no invented government behavior.

## 6. Final coding-agent operating instruction

The coding agent must act as a senior software engineer receiving a complete handoff. It must:

1. Read the complete specification before coding.
2. Inspect the existing repository before modifying anything.
3. Build and maintain a requirement checklist.
4. Implement the local application foundation first.
5. Implement data import/validation and SQLite state management.
6. Implement workflow state machines and audit/event recording.
7. Implement the browser adapter architecture.
8. Implement one verified workflow at a time.
9. Add UI-change resilience before scaling to batch processing.
10. Test success, failure, interruption, duplicate, retry, resume, and unknown-state cases.
11. Never repeat a consequential portal action merely because the previous confirmation was lost; verify the current portal state first.
12. Never update spreadsheet success state based solely on an attempted click.
13. Never fabricate missing portal behavior.
14. Do not ask the user questions that this specification already answers.
15. Make ordinary internal engineering decisions autonomously.
16. Ask for human intervention only when a genuinely unknown government-portal behavior, security challenge, authorization decision, or future source recording is required.
17. Keep future undocumented workflows behind explicit adapters and `MANUAL_REQUIRED` / `COMING_SOON` states.
18. At completion, report implemented requirements, tests, remaining manual/Coming-Soon workflows, and any live-portal verification that still requires the operator.

---

# PEN IMPORT — OTHER SCHOOL ACTIVE — COMPLETE OBSERVED WORKFLOW

> **Correction, 2026-09-25.** This section supersedes the earlier
> placeholder statements that the PEN Import screens/actions were "not yet
> documented" (this document, section 68, "The exact PEN import
> screens/actions are not yet documented.") and that "the exact portal
> screen, button names, confirmation message, and field locations must be
> documented from the dedicated Import recordings rather than invented"
> (the "PEN IMPORT — REQUIRED FINAL STATE" §295.3 note, as applied to this
> specific recording). Those statements should not be treated as still-open
> requirements for **this** recording — the user re-checked
> `PEN IMPORT (OTHER SCHOOL ACTIVE).mp4` directly and supplied the complete
> observed workflow below, which is now authoritative for this recording.
> The old statements remain accurate for whatever they were not re-verified
> against (e.g. the successful/Dropbox PEN Import path, which this
> recording does not demonstrate — see section 19/26 below).

Source recording: `PEN IMPORT (OTHER SCHOOL ACTIVE).mp4`
Duration: approximately 3 minutes 55 seconds
Portal: UDISE+ Student Database Management System
Purpose: Determine whether the student's Aadhaar is already associated
with a student in another school, identify the existing student's
PEN/source-school information, verify the source school's Head of School
details, and record the student in the IMPORT PENDING worksheet when the
source student is still ACTIVE.

**Important:** This workflow is specifically the Other School ACTIVE case.
It is different from the PEN REQUEST SENT workflow. This recording does
not demonstrate successful import and does not demonstrate sending a
transfer/import request. It demonstrates identification of an existing
student who remains ACTIVE in another school and recording that case for
later import processing.

## 1. Starting Data — PEN Workbook

The operator starts from:

`PEN_Entry_(National).xlsx`

The workbook contains:

`PH1`, `PH2`, `PH3`, `IMPORT PENDING`

The demonstrated student is:

`D MANASHI PATRA`

The student's PEN is not initially present in the normal school-entry row.
The student's Aadhaar is available in the PEN entry data. The purpose of
this workflow is to determine whether the Aadhaar already belongs to a
student in another school.

## 2. Open UDISE+ Portal

The operator uses the National UDISE+ Student Database Management System.

Observed portal context:

- UDISE+ branding
- Student Database Management System
- School UDISE Code: `24224100067`
- School: `SATYAM STARS INTERNATIONAL SCHOOL`
- Academic Year: `2026-27`
- School user account is already logged in.

The application must not hardcode the visible user name or password.

## 3. Navigate to Add New Student

The observed portal screen is:

**Add New Student**

The page displays the selected: Class, Section, Academic Year.

The example shows:

- Class: `UKG/KG2/PP1`
- Section: `A`
- Academic Year: `2026-27`

These are example values from the recording and must not be hardcoded.
The class must be derived from the student's actual PEN/UDISE spreadsheet
record.

## 4. Enable Aadhaar Availability Check

At the top of the Add New Student page there is:

**Check AADHAAR Number Availability**

The operator enables/checks this option. The page then provides an
Aadhaar-number input and a **Go** button.

## 5. Enter Student Aadhaar

The operator enters the student's Aadhaar number. For the demonstrated
student (`D MANASHI PATRA`), the Aadhaar value is taken from the
spreadsheet/source student record.

The application must:

1. read the student's Aadhaar from the configured data source;
2. validate that it is present and structurally valid;
3. enter it into the Aadhaar field;
4. click/use Go;
5. wait for the portal response.

Do not proceed based merely on the click. The portal response must be
inspected.

## 6. Aadhaar Duplicate/Existing-Student Detection

The demonstrated portal response is a modal:

**"AADHAAR number is already registered with some other student"**

The modal/screen provides a **View Details** control (an **Okay**
dismissal may also be present on the modal itself — the operative next
action for the automation is `View Details`, not merely dismissing the
modal). This is a critical business signal. It means:

```text
Student is NOT a normal new PEN student
        ↓
Aadhaar already exists in another student record
        ↓
Investigate existing student
        ↓
Determine whether existing student is in another school
```

The automation must classify this as `EXISTING_STUDENT_FOUND_BY_AADHAAR`
and must not continue with ordinary New Student creation.

## 7. View Details

The operator selects **View Details**. The portal opens **Track By
Details** — this exact observed screen name must be used; do not replace
it with generic wording such as "Existing Student Details," "Duplicate
Student Details," or "Search Results." This is an important observed
behavior — the automation should wait for the Track By Details state
rather than immediately navigating elsewhere.

## 8. Track By Details

The observed modal title is **Track By Details**. The modal displays a
row containing:

| Field | Observed information |
|---|---|
| S.No. | 1 |
| UDISE Code | `21196100152` |
| School Name | `BAL BHARATI ENGLISH MEDIUM SCHOOL` |
| Student PEN | `23131637482` |
| Student Name | `D MANASHI PATRA` |
| Class | `Pre-primary` |
| Section | `A` |
| HOS | Headmaster/Principal details |

The observed Head of School information includes:

- Headmaster/Principal: `Sasmita Prusty`
- Designation: `1 - Head Master/Principal`
- Contact No.: `8439518463`

These are video example values, not constants.

## 9. Student Identity Verification

The automation must verify that the student returned by the portal
corresponds to the intended spreadsheet student. At minimum compare
available identity attributes: Student Name, Aadhaar-related identity
where available, PEN if already known, DOB where available, Class, parent
information where available.

For the demonstrated case: requested student `D MANASHI PATRA`, portal
result `D MANASHI PATRA` — the name matches.

The automation must not assume that a duplicate Aadhaar automatically
means the first returned student is the correct student if multiple
records are ever returned.

If multiple candidates appear:

```text
STOP
    ↓
Present candidates
    ↓
Require identity matching/manual review
```

Do not arbitrarily select a record.

## 10. Close/Leave Track By Details

The Track By Details modal provides the initial source-school
information. The application should capture this information into its
internal workflow state before leaving the screen.

Important fields to capture when available: source UDISE code, source
school name, existing PEN, student name, source class, source section,
Headmaster/Principal, designation, contact number. The exact fields
returned by the portal may vary.

## 11. Global Student Search

The recording then uses the portal's **Global Student Search** menu.
Observed left navigation contains Global Student Search. The screen
provides multiple search modes; the demonstrated workflow specifically
uses **Student PEN**. The operator selects the Student PEN search option.
The PEN obtained from the Track By Details result is entered — for the
example, `23131637482`. Then the operator clicks **Search**.

## 12. Global Student Search Result

The portal returns a student result. The visible result table contains
columns including: S.No., Student Name, Permanent Education Number (PEN),
DOB, Parent Details, Mobile Number, School Details, Academic Year / Class,
Student Status, HOS Details.

For the demonstrated student (`D MANASHI PATRA`) the result shows:

- PEN: `23131637482`
- Student Status: `ACTIVE`
- Current/source school: `BAL BHARATI ENGLISH MEDIUM SCHOOL`
- School UDISE: `21195100152`
- Academic Year: `2026-27`
- Current Class: `UKG/KG2/PP1`

The exact DOB should be read from the portal when required; the video
does not provide sufficiently reliable evidence for the specification to
hardcode a specific DOB value.

## 13. Critical Decision — Student Status

The most important field at this stage is **Student Status**. The
demonstrated result is `ACTIVE` — the student is still active in the
other school. Therefore:

```text
PEN exists
      ↓
Student exists in another school
      ↓
Student Status = ACTIVE
      ↓
Immediate import is NOT completed
      ↓
Case becomes IMPORT PENDING
```

This is the Other School ACTIVE business condition. The case must be
classified as `PEN_IMPORT_OTHER_SCHOOL_ACTIVE`. Do NOT classify this as
successful import. Do NOT classify this as `REQUEST SENT`. Do NOT mark
the case GREEN merely because the existing PEN was found.

**PEN provenance.** The PEN discovered through Track By Details / Global
Student Search is an **existing** PEN (`pen_source = SOURCE_SCHOOL_EXISTING`),
not a newly generated one — preserve this provenance where practical. Do
not generate a replacement PEN, use UID as PEN, or fabricate a temporary
PEN.

## 14. HOS Details

The result contains an **HOS Details** button. The operator opens it. A
modal titled **HOS Details** appears. The observed information includes:

- State: `ODISHA`
- District: `GANJAM`
- Block: `SHERAGADA`
- Headmaster/Principal: `Sasmita Prusty`
- Contact No.: `8439518463`

Again, these values are examples from the recording. The automation
should extract the actual values returned for the current student.

## 15. Close HOS Details

After recording the source-school information, close the HOS Details
modal. No transfer request is sent in this workflow. No import-success
operation is performed.

## 16. Build IMPORT PENDING Record

The operator then updates `PEN_Entry_(National).xlsx` → `IMPORT PENDING`.
The existing IMPORT PENDING sheet has: `SR NO, STUDENT NAME, PEN, DOB,
SCHOOL NAME, SCHOOL UDISE, STATE, DISTRICT, BLOCK, HEADMASTER, CONTACT NO,
STATUS, REMARK`.

The demonstrated student is added as a new pending record. Observed
resulting values include:

| Field | Example |
|---|---|
| STUDENT NAME | `D MANASHI PATRA` |
| PEN | `23131637482` |
| SCHOOL NAME | `BAL BHARATI ENGLISH MEDIUM SCHOOL` |
| SCHOOL UDISE | `21195100152` |
| STATE | `ODISHA` |
| DISTRICT | `GANJAM` |
| BLOCK | `SHERAGADA` |
| HEADMASTER | `Sasmita Prusty` |
| CONTACT NO | `8439518463` |
| STATUS | `ACTIVE` |

The recording does not establish a reliable mandatory value for every
column in every case, so the application must not invent missing values.

## 17. IMPORT PENDING Business State

The final business state is:

```text
Student Aadhaar checked
        ↓
Aadhaar already registered elsewhere
        ↓
Existing student identified
        ↓
PEN identified
        ↓
Source school identified
        ↓
Global Student Search performed
        ↓
Student Status = ACTIVE
        ↓
HOS details verified
        ↓
IMPORT PENDING record created/updated
```

This is not `IMPORT SUCCESSFUL` and it is not `REQUEST SENT`. Those are
separate states.

## 18. Spreadsheet Status Rule

The user's established business rule is:

```text
Other School ACTIVE
        ↓
Import cannot currently complete
        ↓
Main applicable student record
        ↓
LIGHT ORANGE
        ↓
REMARK = IMPORT PENDING
```

The IMPORT PENDING worksheet receives/maintains the source-school details
and current status.

**Important distinction.** LIGHT ORANGE and REQUEST SENT are not
synonymous. For this workflow: `IMPORT PENDING` = student remains ACTIVE
in another school = import has not completed. Whereas `REQUEST SENT` = a
transfer/request action has actually been submitted. The PEN Import
ACTIVE workflow must not automatically change `IMPORT PENDING` into
`REQUEST SENT` unless a separate documented workflow explicitly performs
that action.

## 19. What This Recording Does NOT Demonstrate

The recording does not establish the following: successful import from
the other school's Dropbox; successful transfer/import completion; a
portal Import button; a success message for Import; automatic removal
from the source school; automatic creation of a new destination record;
automatic PEN reassignment; a transfer request being sent; approval of a
transfer request; destination-side acceptance; completed import;
successful PEN migration.

Therefore, the coding agent must not invent those steps for this
workflow. Those belong to other workflow recordings or future documented
workflows.

## 20. Difference From PEN REQUEST SENT

The application must explicitly distinguish these two workflows.

**PEN Other School ACTIVE:**
```text
Aadhaar check → Aadhaar already registered → Track By Details →
Existing PEN → Global Student Search → Student Status = ACTIVE →
HOS Details → IMPORT PENDING sheet → IMPORT PENDING / LIGHT ORANGE
```

**PEN REQUEST SENT:**
```text
Existing student identified → Request/transfer action →
Portal request submitted → REQUEST SENT → LIGHT ORANGE →
Later approval/status monitoring
```

Do not merge these workflows.

## 21. Automation State Machine

```text
PEN_IMPORT_START
      ↓
OPEN_ADD_NEW_STUDENT
      ↓
CHECK_AADHAAR_AVAILABILITY
      ↓
ENTER_AADHAAR
      ↓
SUBMIT_AADHAAR_CHECK
      ↓
┌─────────────────────────────────────┐
│ Portal result                       │
├─────────────────────────────────────┤
│ Aadhaar available → NEW path        │
│ Aadhaar already registered →        │
│ existing-student path               │
│ Unknown/error → MANUAL_REQUIRED     │
└─────────────────────────────────────┘
                    ↓
        EXISTING_STUDENT_FOUND
                    ↓
          READ_TRACK_BY_DETAILS
                    ↓
          VERIFY_STUDENT_IDENTITY
                    ↓
          OPEN_GLOBAL_STUDENT_SEARCH
                    ↓
             SEARCH_BY_PEN
                    ↓
            READ_STUDENT_RESULT
                    ↓
        VERIFY STUDENT STATUS
                    ↓
              ┌─────┴─────┐
              │           │
           ACTIVE      NOT ACTIVE /
              │         UNKNOWN
              │           │
              ▼           ▼
        READ HOS       MANUAL /
         DETAILS       FUTURE
              │
              ▼
      WRITE IMPORT PENDING
              │
              ▼
        IMPORT_PENDING
              │
              ▼
      LIGHT ORANGE
```

The NOT ACTIVE / UNKNOWN branch must not be invented from this recording.
It should be routed to the appropriate documented workflow or
`MANUAL_REQUIRED`.

## 22. Required Verification Before IMPORT PENDING Update

Before writing the pending record, the automation must verify:

- **Student**: name matches; PEN is valid/11-digit; portal result belongs
  to the intended student.
- **Source school**: school name, UDISE, state, district, block captured.
- **HOS**: Headmaster/Principal and contact number captured when
  available.
- **Status**: portal explicitly shows `ACTIVE`.

Only then should the automation classify the case as
`IMPORT_PENDING_ACTIVE_OTHER_SCHOOL`.

## 23. Failure Handling

- **Aadhaar check fails** — do not continue; record
  `PEN_AADHAAR_CHECK_FAILED`.
- **Aadhaar duplicate message appears but Track By Details does not
  load** — do not guess; record `PEN_EXISTING_STUDENT_DETAILS_UNAVAILABLE`
  and require manual review.
- **Multiple students returned** — do not automatically select one;
  record `PEN_STUDENT_MATCH_AMBIGUOUS`.
- **PEN search returns no student** — do not create a fake pending
  record; record `PEN_SEARCH_NO_RESULT`.
- **Student status is not ACTIVE** — do not classify it as Other School
  ACTIVE; route to the documented status-specific workflow.
- **HOS Details unavailable** — do not fabricate Headmaster/contact
  information; preserve the available source-school data and mark the
  missing fields appropriately for manual review if they are required.
- **Spreadsheet write fails** — do not repeat the portal lookup
  unnecessarily; preserve the verified portal state in SQLite and retry
  only the spreadsheet operation.

## 24. Idempotency

If UdiFy restarts after the portal lookup has already succeeded:

- Do not repeat Aadhaar check blindly.
- Do not create duplicate IMPORT PENDING rows.
- Do not repeat unrelated portal actions.

Instead: check SQLite workflow state; check whether the student already
exists in IMPORT PENDING; match by stable identifiers (student ID/name,
PEN, UID where available, source-school UDISE); update the existing
pending record if appropriate; preserve history.

## 25. Critical Implementation Rule

The automation must never interpret **"AADHAAR number is already
registered with some other student"** as an error that stops the entire
workflow. It is a business-routing signal:

```text
Aadhaar duplicate
        ↓
Student already exists
        ↓
Investigate existing record
        ↓
Determine source school/status
```

The automation should therefore transition into the existing-student/
import investigation workflow.

## 26. Exact Observed Screen Sequence

```text
UDISE+ Login
      ↓
School Dashboard
      ↓
Add New Student
      ↓
Check AADHAAR Number Availability
      ↓
Aadhaar input
      ↓
Go
      ↓
Modal: "AADHAAR number is already registered with some other student"
      ↓
Okay
      ↓
Track By Details
      ↓
Existing student + PEN + source school
      ↓
Global Student Search
      ↓
Student PEN selected
      ↓
PEN entered
      ↓
Search
      ↓
Student result
      ↓
Student Status = ACTIVE
      ↓
HOS Details
      ↓
State / District / Block / Headmaster / Contact
      ↓
Close HOS Details
      ↓
PEN_Entry_(National) → IMPORT PENDING
      ↓
Append/update student record
      ↓
STATUS = ACTIVE
      ↓
IMPORT PENDING business state
```

## 27. Final correction to the old specification

The old statements —

> "The exact portal screen, button names, confirmation message, and field
> locations must be documented from the dedicated Import recordings rather
> than invented."

and

> "PEN Import — exact portal mechanics still being documented"

— should not remain as unresolved requirements for this particular
recording. They are replaced by the complete workflow above.

**The successful PEN Import/Dropbox path remains a separate, still-open
workflow boundary** — it was not demonstrated in this recording. The
coding agent must not infer the Dropbox/successful-import path from this
ACTIVE-workflow documentation; it stays `COMING_SOON` in the right places
of this specification (the outcome rule at section 295 of the "PEN IMPORT
— REQUIRED FINAL STATE" area still applies to that separate path).

---

# PEN REQUEST SENT — STUDENT RELEASE REQUEST WORKFLOW

> **Correction, 2026-09-25.** This section incorporates
> `PEN REQUEST SENT .mp4`, previously listed as "Incorporated" in the
> source inventory without its content ever being transcribed. **Status:
> DOCUMENTED FROM RECORDING.** This is a National UDISE+ portal workflow —
> it is **not** the same screen as the Gujarat Child Tracking System's
> transfer-request screen (see "PEN REQUEST SENT vs UDISE REQUEST SENT"
> below for how the two relate).

Source: `PEN REQUEST SENT .mp4`. This recording demonstrates the National
UDISE+ **student release-request** workflow.

## 1. Student Release Request Management

The observed portal menu is **Student Release Request Management**,
providing four functions — preserve these exact observed labels, do not
replace them with generic names:

1. `Generate Student Release Request Within State`
2. `Approve Student Release Request(s) Within State`
3. `View Student Release Request(s) Within State (Inbox)`
4. `View Student Release Request(s) Within State (Sent)`

## 2. Generate Student Release Request Within State

The operator selects **Generate Student Release Request Within State**.
The page states that the request requires PEN and DOB, and is for an
active student:

```text
Student Release Request Management
        ↓
Generate Student Release Request Within State
        ↓
Enter PEN
        ↓
Enter DOB
        ↓
Get Details
```

## 3. Get Details

The operator provides Permanent Education Number (PEN) and Date of Birth,
and selects **Get Details**. The portal retrieves **Student Basic Details
(as Per School record/School Admission Register)**, displaying fields
including: UDISE Code, School Name, Student Name, Gender, DOB, PEN,
Student State Code, Mother's Name, Father's Name, Aadhaar No., Name as per
Aadhaar, Aadhaar Capture Status.

The automation must verify the returned student before generating a
release request (same multi-attribute identity rule as the rest of this
specification — spec Final Authority §E).

## 4. Student Admission Detail

The page contains **Student Admission Detail** with observed fields:
Class, Section, Date of Admission, Select Remark. The operator
supplies/selects the destination admission information. The recording
demonstrates a release remark equivalent to "Please release the student
from the school records" — if the portal provides this as a selectable
option, select the actual portal option rather than typing free text.

## 5. Generate Student Release Request + Confirmation

The page contains **Generate Student Release Request**. Because this is a
consequential action, the automation must not treat the button click as
success — the portal presents a confirmation dialog asking whether to
generate the request based on the student's current class and selected
class, with **Cancel** / **Confirm**. This is a mandatory verification
checkpoint: verify student identity, PEN, DOB, current class, selected
class, and destination context before confirming.

## 6. Successful Request Generation

After **Confirm**, the portal displays a success message equivalent to
**"Release Request successfully generated"** and provides a **Request
No.** The demonstrated request number is `SR/GJ/GJ/305364710` (example
only — never hardcode). This request number is a critical identifier and
must be captured.

## 7. Request ID Storage

For every generated National release request, store: Request ID/Request
No., PEN, Student ID, Student Name, DOB, Source School UDISE, Source
School Name, Destination School UDISE, Destination School Name, Request
Type, Portal, Request Creation Time, Initial Status, Performed By,
evidence/screenshot reference where configured. Do not rely only on
spreadsheet text — persist the request ID in SQLite.

## 8. REQUEST SENT Business State

Once the portal has confirmed "Release Request successfully generated,"
the business state becomes `REQUEST_SENT` and the spreadsheet operational
state is `REMARK = REQUEST SENT`, `LIGHT ORANGE`. Do not mark GREEN merely
because the request was generated — generating a request is not the same
as the student being imported.

---

# PEN REQUEST SENT vs UDISE REQUEST SENT — SAME CONCEPT, DIFFERENT PORTAL

**Same business concept, different portal implementation.** Both
represent a request to release/transfer a student from an existing
source-school record so the destination school can proceed. However:

- **Gujarat UDISE workflow** uses the Gujarat Child Tracking System's
  `Student Transfer Request List` (Sent/Received/Completed Transfer
  Requests, `REQUEST SENT` — spec §X).
- **National PEN workflow** uses `Student Release Request Management`
  (Generate/Approve/View Inbox/View Sent — this document, above).

```text
COMMON BUSINESS CONCEPT
        ↓
Transfer / Release Request
        │
        ├── Gujarat UDISE Adapter → Transfer Request
        │
        └── National PEN Adapter → Student Release Request
```

Do NOT implement them as one identical browser workflow. Do NOT assume
their selectors, screens, status values, URLs, or request-ID formats are
interchangeable. Use a shared business abstraction with separate portal
adapters.

---

# HOW TO VIEW SENT REQUEST — VIEWING NATIONAL RELEASE REQUEST STATUS

> **Correction, 2026-09-25.** Incorporates `HOW TO VIEW SENT REQUEST.mp4`.
> **Status: DOCUMENTED FROM RECORDING.**

Source: `HOW TO VIEW SENT REQUEST.mp4`. Also on the National UDISE+
portal.

## 1. Navigation

```text
Student Release Request Management
        ↓
View Student Release Request(s) Within State (Sent)
```

## 2. Sent Request Page

The page is **View Student Release Request(s) Within State (Sent)**. It
contains an **Inbox (Request List) (All Requests)** area and a **Request
Status** filter. The table provides request records with observed
columns: S.No., Request No./PEN, Requested By, Requested To, Closed/Auto
Closed By, Request Status, Action. The exact current portal DOM must be
discovered dynamically (spec Final Authority §B selector strategy).

## 3. Exact Observed Status

The demonstrated request shows **"Pending at Destination"** — this exact
phrase is the known canonical observed status; do not document it merely
as "Pending" or hedge it as "or equivalent." The implementation must
still support future portal wording changes through a normalized status
layer:

```text
raw_portal_status:  "Pending at Destination"
normalized_status:  PENDING_AT_DESTINATION
```

The raw wording must always be preserved. If a future status doesn't map
to a known normalized value, record `UNKNOWN_PORTAL_STATUS` and route to
manual review — never silently map an unknown status.

## 4. Observed Request List Values (examples — never hardcode)

- Request No.: `SR/GJ/GJ/305364710`
- PEN: `23428960733`
- Requested By: Satyam Stars International School / destination-school
  context
- Requested To: source-school context
- Closed / Auto Closed By: `NA`
- Request Status: `Pending at Destination`

## 5. Student Details Snapshot

The Sent Requests table provides **Student Details** — the operator can
open the request's student snapshot, shown as **"Student Details (At the
time the request was generated)"**: Request No., PEN, Student Name,
Mother's Name, DOB, Father's Name, Class. Use this to verify the request
belongs to the intended student before acting on it.

---

# APPROVAL MONITORING — CONCRETE NATIONAL PEN IMPLEMENTATION

The existing batched approval-check requirement (spec §M) now has a
concrete National-portal implementation, alongside the Gujarat-side one
(spec §X's Student Transfer Request List):

```text
LIGHT ORANGE + REQUEST SENT
        ↓
User authorizes batch status check (ONE confirmation, not per student)
        ↓
Student Release Request Management → View Student Release Request(s)
Within State (Sent)
        ↓
Read request list → Match Request No./PEN/student → Read Request Status
        ↓
Preserve exact raw portal status → Normalize status internally
        ↓
Record status history
```

**Pending at Destination** → no further automatic action; the student
stays in the pending monitoring population; the check event is recorded.

**Status changed** (`previous_status != current_status`) → record
`STATUS_CHANGED`, preserving previous status, current raw status,
normalized status, timestamp, request ID, student identity, spreadsheet
status/color; notify the operator; place the student in manual review.
Do NOT automatically execute the next consequential portal action.

`View Details` (student identity, PEN, request number, source/destination
school, current/previous/normalized status, spreadsheet status/color,
history, last-checked time/by, evidence) / `Take Next Action` (opens the
relevant National request status page — the operator acts manually, the
automation never performs the consequential action itself) / `Mark Action
Completed` (requires an action description; records performed_by=MANUAL,
timestamp, request ID, previous/current status) all apply identically to
these National request records as they do to the Gujarat-side ones (spec
§N). A status-changed case stays open until explicitly resolved
(resolution note required); reopening a resolved case requires a
`reopen_reason` and creates a new case cycle — the original resolution
stays immutable history (spec §S).

---

# SHARED REQUEST-CASE MODEL AND DATABASE STATE REQUIREMENTS

## Common business model

```text
                    REQUEST CASE
                         │
              ┌──────────┴──────────┐
              │                     │
       STATE UDISE              NATIONAL PEN
              │                     │
     TRANSFER REQUEST          RELEASE REQUEST
              │                     │
       Gujarat portal          UDISE+ portal
```

Shared concepts: request generated, request ID, request sent, pending,
status monitoring, status change, manual review, resolution. Portal-
specific concepts: screen names, selectors, URLs/routes, exact raw
statuses, request-number format, buttons, confirmation dialogs,
source/destination terminology, status pages.

## Do NOT collapse IMPORT PENDING and REQUEST SENT

These are different states, both rendered as LIGHT ORANGE, and the
database — not the color — must distinguish them:

- **IMPORT PENDING** = the student exists at another school AND is ACTIVE
  there AND import has not completed AND this workflow has not
  necessarily generated a release request. Spreadsheet: `IMPORT PENDING`,
  LIGHT ORANGE.
- **REQUEST SENT** = a release/transfer request was actually generated
  successfully AND the portal returned a request number. Spreadsheet:
  `REQUEST SENT`, LIGHT ORANGE.

## Database state requirement

Do not rely solely on spreadsheet color or remark internally. Use
structured fields:

```text
case_type:     IMPORT_PENDING_ACTIVE | RELEASE_REQUEST_SENT | TRANSFER_REQUEST_SENT
portal:        NATIONAL_UDISE | GUJARAT_UDISE
request_type:  NONE | RELEASE_REQUEST | TRANSFER_REQUEST
```

A student can therefore be `case_type = IMPORT_PENDING_ACTIVE,
request_type = NONE` or `case_type = RELEASE_REQUEST_SENT, request_type =
RELEASE_REQUEST` — never represent both internally as simply
`LIGHT_ORANGE`. Color is presentation; business state belongs in the
database (extends DB-DESIGN.md §B/§C.3a — see that file for the concrete
table/event-code mapping).

## Exact status preservation

Store BOTH `raw_portal_status` and `normalized_status` for every portal
status read (UDISE and PEN alike), per the pattern in "HOW TO VIEW SENT
REQUEST" section 3 above. This is mandatory, not optional, for every
status-bearing workflow in this specification.

---

# CONDITION 4 AND THE DROPBOX-PATH BOUNDARY — FINAL STATEMENT

**Condition 4** (`UDISE + PEN both imported`) is a business condition,
not an independently recorded end-to-end workflow:

```text
Condition 4 is composed from independently documented workflow branches.
It is not a separately recorded end-to-end workflow.
UdiFy may compose the branches only after each branch's entry/exit
conditions are satisfied and independently verified.
```

**UDISE Import's successful Dropbox path was NOT demonstrated.** The
observed UDISE Import recording (spec §X) documents only the
ACTIVE-at-other-school path (Manage Students → Standard Wise Entry →
class → search UID → existing student at another school → transfer
confirmation → Transfer Student → Transfer From/To → `Update Transfer
Request` → "Student Transfer request saved successfully." → `REQUEST
SENT`). Do not invent an Import button, a Dropbox screen, a success
message, or automatic import mechanics for either UDISE or PEN's
successful outcome.

---

# FINAL DOCUMENTATION CLASSIFICATION

```text
PEN IMPORT (OTHER SCHOOL ACTIVE)
STATUS: DOCUMENTED / OBSERVED

PEN REQUEST SENT
STATUS: DOCUMENTED / OBSERVED

HOW TO VIEW SENT REQUEST
STATUS: DOCUMENTED / OBSERVED

UDISE IMPORT — successful Dropbox path
STATUS: BUSINESS RULE DEFINED / CLICK-LEVEL WORKFLOW NOT DEMONSTRATED

PEN IMPORT — successful Dropbox path
STATUS: BUSINESS RULE DEFINED / CLICK-LEVEL WORKFLOW NOT DEMONSTRATED

CONDITION 4 (combined UDISE + PEN import)
STATUS: COMPOSITE BUSINESS WORKFLOW / NOT INDEPENDENTLY VIDEO-DEMONSTRATED
```

---

# ACCEPTANCE TESTS — PEN IMPORT / PEN REQUEST SENT / VIEW SENT REQUEST

## Test A — PEN Other School Active

Given a student whose Aadhaar already exists elsewhere: open Add New
Student → check Aadhaar availability → enter Aadhaar → Go → detect
"AADHAAR number is already registered with some other student" → open
View Details → read Track By Details → match student → capture existing
PEN → open Global Student Search → select Student PEN → search by PEN →
confirm student → read Student Status → detect ACTIVE → open HOS Details
→ capture source-school information → update main PEN record with
existing PEN (`pen_source = SOURCE_SCHOOL_EXISTING`) → update `IMPORT
PENDING` → preserve `STATUS = ACTIVE` → apply LIGHT ORANGE → do not mark
GREEN → do not mark REQUEST SENT.

## Test B — PEN Release Request

Given an eligible active source-school student: open Student Release
Request Management → select Generate Student Release Request Within
State → enter PEN → enter DOB → Get Details → verify student → verify
admission details → select the appropriate remark → Generate Student
Release Request → verify confirmation dialog → Confirm → verify success
message → capture Request No. → persist Request No. → set business state
`REQUEST_SENT` → set spreadsheet remark `REQUEST SENT` → apply LIGHT
ORANGE → do not mark GREEN.

## Test C — View Sent Request

Open Student Release Request Management → select View Student Release
Request(s) Within State (Sent) → read request table → match
Request No./PEN/student → read raw status → preserve exact status →
normalize status → record history → for `Pending at Destination`, leave
`REQUEST SENT`/LIGHT ORANGE unchanged → for changed/unknown status,
create a manual-review case.

---

# FINAL INSTRUCTION TO THE CODING AGENT — PEN IMPORT / REQUEST SENT / SENT REQUEST MONITORING

The videos for these three workflows have already been supplied and
analyzed. Do not respond to this specification by asking for them again,
by saying any of these workflows are "still unclear," or by treating them
as unresolved — they are `DOCUMENTED / OBSERVED` per the classification
above. Do not merge the National PEN release-request workflow with the
Gujarat UDISE transfer-request workflow (they share a business
abstraction, not an implementation). Do not invent the successful
Dropbox-import workflow for either portal, and do not invent any portal
behavior not demonstrated by a recording.

Responsibilities when implementing these three workflows: incorporate the
observed workflows as documented above; preserve exact observed portal
terminology (`View Details`, `Track By Details`, `Global Student Search`,
`Student Release Request Management`, `Pending at Destination`, etc.);
implement separate portal adapters sharing the common request-case
abstraction; preserve raw portal status and normalize known statuses
separately; verify every consequential action before recording it;
implement resilient selectors per spec Final Authority §B; maintain audit
history and idempotency; prevent duplicate requests, false GREEN, false
`REQUEST SENT`, and false import success; preserve manual-review
boundaries; keep TODO.md/BOOTSTRAP.md/the implementation checklist
in sync so these three workflows are never again marked unresolved,
while genuinely open items (the successful/Dropbox path on either portal,
and Condition 4's full combination) remain honestly marked as such.

---

# UDIFY — CREDENTIALS, MOCKING AND LIVE VERIFICATION DECISION

> **Decision, 2026-09-25.** This section is an authoritative engineering-
> process decision from the project owner, made at the CODING-gate
> threshold (RULEBOOK.md §F). It governs *how* implementation proceeds,
> not the business rules already established elsewhere in this document
> — those are unchanged. It supersedes any implication elsewhere that
> live credentials must be obtained before coding starts.

Proceed with **mock-first development**. Do not wait for Google Sheets
service-account credentials or government-portal credentials before
implementing the system.

> **Build and fully test against mocks first. Real credentials will be
> supplied later for controlled live verification.**

This is an implementation sequencing decision, not a reduction in scope.

## 1. Google Sheets credentials

Do not request or wait for the Google Sheets service-account credentials
at this stage. Implement the complete Google Sheets adapter against a
clearly defined interface. The adapter must support the actual UDIFY
requirements: `ONLINE GENERAL REGISTER`, `UDISE_Entry_(State)`,
`PEN_Entry_(National)`, `PH1`, `PH2`, `PH3`, `IMPORT PENDING`; reading
headers; locating students; reading row values; reading row
colors/status; updating individual cells; updating complete rows where
required; preserving unrelated formatting; setting the required
GREEN/LIGHT ORANGE states; updating PEN from ND when an actual PEN
becomes available; updating OGR PEN when required; spreadsheet-only
recovery after portal success; verification after writes; safe retry
behavior; idempotency.

The implementation must not contain fake hardcoded credentials or depend
on a particular user's service-account file. Use configuration such as
`GOOGLE_SERVICE_ACCOUNT_FILE`, `GOOGLE_SPREADSHEET_ID`, or an equivalent
secure configuration mechanism. Credentials must never be committed into
Git.

## 2. Mock Google Sheets adapter

Create a mock/in-memory Google Sheets implementation that behaves like
the real adapter interface. The mock must allow automated tests for:
reading a student; finding a student by name; finding by UID; finding by
PEN; reading row status; reading row color; writing a cell; writing a
row; changing row color; preserving existing values; simulated write
failure; simulated network failure; retry; duplicate update prevention;
verification failure; spreadsheet-only recovery.

The business logic must depend on the **adapter interface**, not directly
on the Google Sheets SDK:

```text
StudentSheetRepository
        |
        +-- GoogleSheetsRepository
        |
        +-- MockSheetsRepository
```

The workflow engine must be able to run completely with
`MockSheetsRepository`.

## 3. Government portal credentials

Do not request or wait for government credentials during the current
implementation phase. Build the government portal adapters against
mocked pages and deterministic test fixtures. The architecture must
support the real portals later without rewriting the business workflow
engine. Keep the portal concerns separated into adapters such as
`GujaratUDISEPortalAdapter` and `NationalUDISEPortalAdapter` — do not
combine the two portal implementations into one giant browser automation
class. Shared business concepts may be abstracted, but portal-specific
navigation, selectors, statuses, URLs, dialogs, tables and workflows must
remain portal-specific.

## 4. Mock portal pages are mandatory

Implement mocked portal scenarios covering every workflow already
documented from the recordings.

**Gujarat UDISE** (minimum): new UDISE; existing student search;
other-school student found; transfer confirmation; Transfer Student page;
Transfer From/Transfer To; "Student Transfer request saved successfully.";
`REQUEST SENT`; Student Transfer Request List; pending request; session
expiry; timeout; unknown page/state; duplicate-request protection.

**National UDISE+** (minimum): new PEN; successful student
initialization; General Profile; Enrolment Profile; Facility Profile;
"Data completion is complete."; PEN = `NA` on portal; spreadsheet
PEN = `ND`; Aadhaar already registered; `View Details`; `Track By
Details`; existing PEN discovery; Global Student Search; Student
Status = `ACTIVE`; HOS Details; `IMPORT PENDING`; Student Release Request
generation; release confirmation dialog; release request success;
Request No capture; Sent Request list; `Pending at Destination`; Student
Details modal; ND reconciliation; actual 11-digit PEN discovered; PEN
remains unavailable; portal status unknown; session expiry; timeout;
network failure; browser crash; duplicate request prevention.

## 5. Do not fake government success

Mock tests may simulate successful outcomes, but the production
application must distinguish `MOCK_SUCCESS` from `LIVE_VERIFIED_SUCCESS`.
A mock test must never cause the production database or spreadsheet to
claim that a real government operation was completed. The application
should record the environment appropriately: `environment = MOCK` or
`environment = LIVE`. Every consequential live action must be verified
against the actual portal before the corresponding real-world business
state is committed.

## 6. Real credentials must be injectable later

When real credentials are eventually supplied, the agent should only need
to configure the environment — do not redesign the architecture at that
point. Intended sequence:

```text
IMPLEMENT → MOCK TEST → INTEGRATION TEST → STATIC/UNIT TEST →
LIVE CREDENTIAL CONFIGURATION → CONTROLLED LIVE VERIFICATION →
PRODUCTION HARDENING
```

Real credentials must be supplied through secure configuration/
environment mechanisms. Never: hardcode passwords; hardcode CAPTCHA
values; commit service-account JSON; commit government credentials; put
credentials into source code, screenshots, test fixtures, or exception
messages; print passwords into logs.

## 7. CAPTCHA and security controls

Do not attempt to bypass CAPTCHA. The architecture must support
`AUTOMATION_PAUSED_FOR_USER` when a CAPTCHA or other mandatory security
interaction is encountered — the user performs the security step
manually, then automation resumes from a known checkpoint. The same
principle applies to Aadhaar demographic-authentication consent where
manual/user-controlled interaction is required by the documented
workflow.

## 8. Live verification is a separate phase

Once real credentials are supplied, do not immediately process a large
student batch. Perform controlled live verification first, in order:

**Phase L1 — Authentication.** Verify Google Sheets authentication,
Gujarat portal login, National UDISE+ login. Do not expose credentials
in logs.

**Phase L2 — Read-only portal verification.** Verify the adapter can open
the correct portal, identify the expected page, locate expected
navigation, locate student search, read expected student fields, identify
portal status, identify current workflow state. No consequential action
performed unnecessarily.

**Phase L3 — Controlled student verification.** Using a specifically
authorized test/student case, verify identity matching, navigation, field
mapping, selectors, state detection, confirmation handling, success
detection, database event creation, spreadsheet verification.

**Phase L4 — Recovery verification.** Test timeout, session expiry,
browser restart, network interruption, spreadsheet write failure,
unknown UI state, duplicate-action protection.

Only after these checks should larger-scale processing be considered.

## 9. UI-change resilience remains mandatory

Unchanged from the Final Authority section's selector-strategy rule
(this document, section B of "FINAL AUTHORITY — FINAL SPECIFICATION") —
restated here because it applies identically to code built against mocks:
never rely solely on fixed x/y coordinates or `sleep()`+click. After
every consequential action, verify the resulting state. If the portal
changed harmlessly, an approved fallback may be used; if a changed UI
affects a consequential decision and the system cannot determine the
correct state confidently: **STOP, capture diagnostics, preserve the last
verified state, request manual intervention. Never guess.**

## 10. Credentials must not become an implementation blocker

Do not report "Waiting for credentials before development can continue."
Instead report: "Mock implementation and automated verification are
complete; live credential configuration and controlled live verification
remain." That is the correct project state. The absence of live
credentials is an expected dependency for **live verification only**, not
for: architecture; business logic; database; state machine; spreadsheet
adapter interface; portal adapter interface; selector strategy; error
handling; retry logic; checkpointing; event logging; mock testing; UI;
reports; approval history; ND reconciliation logic; request tracking;
unit tests; integration tests using mocks.

## 11. Acceptance requirement

Before requesting real credentials, the agent should be able to
demonstrate that the application can execute the documented workflows
against mocks:

```text
Student → Mock Google Sheet → Workflow Engine → Mock Government Portal →
Portal Result → Verification → SQLite Event → Mock Spreadsheet Update →
Spreadsheet Verification → Final Workflow State
```

The same workflow engine must later support the identical shape with
Real Google Sheet / Real Government Portal / Live Verification / Real
Spreadsheet Update / Real Spreadsheet Verification in place of the mock
equivalents. The business logic must not be rewritten merely because the
implementation changes from mock to live.

## 12. Do not invent undocumented government behavior

Unchanged from elsewhere in this document — restated for emphasis at this
decision point. The recordings remain the authoritative evidence for
currently documented portal workflows. Where a workflow is not
demonstrated (successful Dropbox import; successful post-request import
mechanics; undocumented portal buttons; undocumented approval behavior;
undocumented status transitions; undocumented APIs/endpoints), do not
invent it — mark it `UNDOCUMENTED / NOT IMPLEMENTED` until evidence
exists.

## 13. Final decision and required build order

**Do not provide real credentials now.** Proceed with: (1) complete
architecture; (2) complete Google Sheets adapter interface; (3) mock
Google Sheets adapter; (4) complete Gujarat UDISE adapter interface;
(5) complete National UDISE+ adapter interface; (6) mocked portal pages;
(7) deterministic workflow tests; (8) state-machine tests; (9) idempotency
tests; (10) recovery tests; (11) selector fallback tests; (12) spreadsheet
verification tests; (13) SQLite event/audit tests; (14) approval-history
tests; (15) request-status monitoring tests; (16) ND reconciliation tests;
(17) UI tests; (18) packaging/build tests.

Then stop at the **LIVE VERIFICATION GATE** and report exactly:

```text
MOCK IMPLEMENTATION: COMPLETE / INCOMPLETE
MOCK TESTS: PASS / FAIL
INTEGRATION TESTS: PASS / FAIL
LIVE GOOGLE SHEETS: NOT VERIFIED
LIVE GUJARAT UDISE: NOT VERIFIED
LIVE NATIONAL UDISE+: NOT VERIFIED
LIVE CREDENTIALS: NOT CONFIGURED
```

Do not claim live functionality until it has actually been tested against
the real systems. When credentials are eventually supplied, use them only
for the controlled live-verification phase described in section 8.

**No architectural compromise. No incomplete adapter hidden behind the
absence of credentials. No fake live success. No credential hardcoding.**

**This document is the final engineering specification. Do not replace it with a shorter summary.**
