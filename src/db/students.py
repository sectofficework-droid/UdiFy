"""students table persistence (DB-DESIGN.md §B.4) — normalized identity.

This is NOT the source of truth for student identity (the OGR spreadsheet
is, spec §AF) — it's a local mirror so other tables (`request_cases`,
`workflow_runs`) can carry a foreign key. Upserting here never writes
back to any spreadsheet.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from src.sheets.models import Student


def upsert_student(conn: sqlite3.Connection, student: Student) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO students (
                student_id, name, father_name, mother_name, surname, dob,
                class_name, phase, gr_no, aadhaar_last4, uid_udise, pen,
                ogr_row_ref, udise_row_ref, pen_row_ref, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(student_id) DO UPDATE SET
                name = excluded.name,
                father_name = excluded.father_name,
                mother_name = excluded.mother_name,
                surname = excluded.surname,
                dob = excluded.dob,
                class_name = excluded.class_name,
                phase = excluded.phase,
                gr_no = excluded.gr_no,
                aadhaar_last4 = excluded.aadhaar_last4,
                uid_udise = excluded.uid_udise,
                pen = excluded.pen,
                ogr_row_ref = excluded.ogr_row_ref,
                udise_row_ref = excluded.udise_row_ref,
                pen_row_ref = excluded.pen_row_ref,
                updated_at = excluded.updated_at
            """,
            (
                student.student_id, student.name, student.father_name,
                student.mother_name, student.surname, student.dob,
                student.class_name, student.phase, student.gr_no,
                (student.aadhaar[-4:] if student.aadhaar else None),
                student.uid_udise, student.pen,
                str(student.ogr_row) if student.ogr_row else None,
                str(student.udise_row) if student.udise_row else None,
                str(student.pen_row) if student.pen_row else None,
                now, now,
            ),
        )
