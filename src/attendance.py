"""Attendance recording and management module."""

import datetime
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract

VALID_STATUSES = ("Present", "Absent", "Leave", "Holiday")


def record_attendance(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    attendance_date: datetime.date,
    status: str,
) -> int:
    """Record daily attendance status for an active employee."""
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )
    if attendance_date.weekday() >= 5:
        raise ValueError(
            f"Attendance cannot be recorded on weekends ({attendance_date})."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_id, is_active FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        emp = cursor.fetchone()
        if not emp:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")
        emp_id, is_active = emp
        if not is_active:
            raise ValueError(
                f"Cannot record attendance for inactive employee '{employee_code.strip()}'."
            )

        cursor.execute(
            """
            INSERT INTO attendance (employee_id, attendance_date, status)
            VALUES (%s, %s, %s)
            """,
            (emp_id, attendance_date, status),
        )
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            raise ValueError(
                f"Attendance already recorded for employee '{employee_code}' on {attendance_date}."
            ) from err
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def update_attendance(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    attendance_date: datetime.date,
    status: str,
) -> None:
    """Update status of an existing attendance record."""
    if status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_id FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        emp = cursor.fetchone()
        if not emp:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")
        emp_id = emp[0]

        cursor.execute(
            """
            UPDATE attendance
            SET status = %s
            WHERE employee_id = %s AND attendance_date = %s
            """,
            (status, emp_id, attendance_date),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                f"No existing attendance row found for employee '{employee_code}' on {attendance_date}."
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_attendance(
    conn: MySQLConnectionAbstract,
    employee_code: str | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> list[dict]:
    """Retrieve attendance records with optional filters, ordered by date then employee_code."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    cursor = conn.cursor(dictionary=True)
    try:
        if employee_code is not None:
            cursor.execute(
                "SELECT employee_id FROM employees WHERE employee_code = %s",
                (employee_code.strip(),),
            )
            if not cursor.fetchone():
                raise ValueError(f"Employee '{employee_code.strip()}' not found.")

        cursor.execute(
            """
            SELECT a.attendance_id, a.employee_id, e.employee_code, e.employee_name, a.attendance_date, a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE (%s IS NULL OR e.employee_code = %s)
              AND (%s IS NULL OR a.attendance_date >= %s)
              AND (%s IS NULL OR a.attendance_date <= %s)
            ORDER BY a.attendance_date, e.employee_code
            """,
            (
                employee_code.strip() if employee_code is not None else None,
                employee_code.strip() if employee_code is not None else None,
                start_date,
                start_date,
                end_date,
                end_date,
            ),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def record_holiday(
    conn: MySQLConnectionAbstract,
    holiday_date: datetime.date,
) -> int:
    """Insert a Holiday row for every active employee on holiday_date in one transaction."""
    if holiday_date.weekday() >= 5:
        raise ValueError(
            f"Holidays cannot be recorded on weekends ({holiday_date})."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_id FROM employees WHERE is_active = TRUE ORDER BY employee_id"
        )
        active_employees = [row[0] for row in cursor.fetchall()]
        if not active_employees:
            return 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE e.is_active = TRUE AND a.attendance_date = %s
            """,
            (holiday_date,),
        )
        (existing_count,) = cursor.fetchone()
        if existing_count > 0:
            raise ValueError(
                f"One or more active employees already have attendance records on {holiday_date}."
            )

        holiday_rows = [(emp_id, holiday_date, "Holiday") for emp_id in active_employees]
        cursor.executemany(
            """
            INSERT INTO attendance (employee_id, attendance_date, status)
            VALUES (%s, %s, %s)
            """,
            holiday_rows,
        )
        conn.commit()
        return len(holiday_rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
