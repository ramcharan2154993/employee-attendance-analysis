"""Attendance recording and management module."""

import datetime
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract

VALID_STATUSES = ("Present", "Absent", "Leave", "Holiday")
ALLOWED_DAILY_STATUSES = ("Present", "Absent", "Leave")


class AttendanceConflictError(ValueError):
    """Raised when attendance has already been recorded for one or more employees on a date."""

    def __init__(self, message: str, conflicts: list[dict]):
        super().__init__(message)
        self.conflicts = conflicts


def check_department_attendance_conflicts(
    conn: MySQLConnectionAbstract,
    department: str,
    attendance_date: datetime.date,
) -> list[dict]:
    """Return active employees in a department who already have attendance records on the given date with status."""
    if not department or not department.strip():
        return []

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT e.employee_code, e.employee_name, a.status, a.attendance_id
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE e.department = %s
              AND a.attendance_date = %s
              AND e.is_active = TRUE
            ORDER BY e.employee_code
            """,
            (department.strip(), attendance_date),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def record_department_attendance(
    conn: MySQLConnectionAbstract,
    department: str,
    attendance_date: datetime.date,
    entries: list[dict],
    user_id: int | None = None,
    username: str | None = None,
) -> dict:
    """Record daily attendance atomically for new unrecorded active employees in a department."""
    from src.audit import log_attendance_action
    from src.employees import get_department_employees

    if isinstance(attendance_date, str):
        try:
            attendance_date = datetime.date.fromisoformat(attendance_date.strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid attendance date '{attendance_date}'.") from exc
    elif not isinstance(attendance_date, datetime.date):
        raise ValueError(f"Invalid attendance date type: {type(attendance_date)}.")

    if attendance_date.weekday() >= 5:
        raise ValueError(
            f"Attendance cannot be recorded on weekends ({attendance_date})."
        )

    if not department or not department.strip():
        raise ValueError("Department cannot be blank.")
    dept_name = department.strip()

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM employees WHERE department = %s",
            (dept_name,),
        )
        (dept_count,) = cursor.fetchone()
        if dept_count == 0:
            raise ValueError(f"Department '{dept_name}' does not exist.")

        eligible_employees = get_department_employees(
            conn,
            department=dept_name,
            active_only=True,
            eligible_as_of=attendance_date,
        )
        if not eligible_employees:
            raise ValueError(
                f"No eligible active employees found in department '{dept_name}' on {attendance_date}."
            )

        eligible_map = {emp["employee_code"]: emp for emp in eligible_employees}
        eligible_codes = set(eligible_map.keys())

        # Check existing attendance in department on this date
        emp_ids = [e["employee_id"] for e in eligible_employees]
        placeholders = ", ".join(["%s"] * len(emp_ids))
        cursor.execute(
            f"""
            SELECT e.employee_code, e.employee_name, a.employee_id
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE a.attendance_date = %s AND a.employee_id IN ({placeholders})
            ORDER BY e.employee_code
            """,
            (attendance_date, *emp_ids),
        )
        existing_rows = cursor.fetchall()
        existing_codes = {r[0] for r in existing_rows}
        unrecorded_codes = eligible_codes - existing_codes

        if not entries:
            if not unrecorded_codes:
                raise ValueError(
                    f"All eligible employees in department '{dept_name}' already have attendance recorded on {attendance_date}."
                )
            raise ValueError("No attendance entries provided.")

        seen_codes: set[str] = set()
        validated_rows: list[tuple[int, datetime.date, str]] = []

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid entry format: expected dict, got {type(entry)}.")

            raw_code = entry.get("employee_code") or entry.get("code")
            if not raw_code or not str(raw_code).strip():
                raise ValueError("Employee code cannot be blank in attendance entries.")
            code = str(raw_code).strip()

            if code in seen_codes:
                raise ValueError(f"Duplicate entry for employee '{code}' in submission.")
            seen_codes.add(code)

            if code not in eligible_map:
                raise ValueError(
                    f"Employee '{code}' is not an active eligible member of department '{dept_name}' on {attendance_date}."
                )

            raw_status = entry.get("status")
            if not raw_status or not str(raw_status).strip():
                raise ValueError(f"Status cannot be blank for employee '{code}'.")
            status = str(raw_status).strip().capitalize()

            if status == "Holiday":
                raise ValueError(
                    "Individual attendance cannot be marked as 'Holiday'. Use record_holiday() for organization holidays."
                )
            if status not in ALLOWED_DAILY_STATUSES:
                raise ValueError(
                    f"Invalid status '{status}' for employee '{code}'. Must be one of: {', '.join(ALLOWED_DAILY_STATUSES)}"
                )

            emp_id = eligible_map[code]["employee_id"]
            validated_rows.append((emp_id, attendance_date, status))

        # Check for conflict among submitted entries
        conflicts = [
            {"employee_code": r[0], "employee_name": r[1]}
            for r in existing_rows
            if r[0] in seen_codes
        ]
        if conflicts:
            conflict_details = ", ".join(
                f"{c['employee_code']} ({c['employee_name']})" for c in conflicts
            )
            raise AttendanceConflictError(
                f"Attendance already recorded for {len(conflicts)} employee(s) on {attendance_date}: {conflict_details}.",
                conflicts=conflicts,
            )

        # Check if any unrecorded eligible employee was omitted from submission
        missing_codes = unrecorded_codes - seen_codes
        if missing_codes:
            missing_str = ", ".join(sorted(missing_codes))
            raise ValueError(
                f"Missing attendance entries for eligible employees: {missing_str}."
            )

        cursor.executemany(
            """
            INSERT INTO attendance (employee_id, attendance_date, status)
            VALUES (%s, %s, %s)
            """,
            validated_rows,
        )

        for emp_id, a_date, st in validated_rows:
            log_attendance_action(
                conn,
                employee_id=emp_id,
                attendance_date=a_date,
                action_type="CREATE",
                new_status=st,
                user_id=user_id,
                username=username,
            )

        conn.commit()

        present_count = sum(1 for _, _, st in validated_rows if st == "Present")
        absent_count = sum(1 for _, _, st in validated_rows if st == "Absent")
        leave_count = sum(1 for _, _, st in validated_rows if st == "Leave")

        return {
            "department": dept_name,
            "attendance_date": attendance_date,
            "total_records": len(validated_rows),
            "present_count": present_count,
            "absent_count": absent_count,
            "leave_count": leave_count,
        }
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            raise ValueError(
                f"Attendance record already exists for one or more employees on {attendance_date}."
            ) from err
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def record_attendance(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    attendance_date: datetime.date,
    status: str,
    user_id: int | None = None,
    username: str | None = None,
) -> int:
    """Record daily attendance status for an active employee."""
    from src.audit import log_attendance_action

    if status == "Holiday":
        raise ValueError(
            "Individual attendance cannot be marked as 'Holiday'. Use record_holiday() for organization holidays."
        )
    if status not in ALLOWED_DAILY_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(ALLOWED_DAILY_STATUSES)}"
        )
    if attendance_date.weekday() >= 5:
        raise ValueError(
            f"Attendance cannot be recorded on weekends ({attendance_date})."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_id, is_active, joining_date FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        emp = cursor.fetchone()
        if not emp:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")
        emp_id, is_active, joining_date = emp
        if not is_active:
            raise ValueError(
                f"Cannot record attendance for inactive employee '{employee_code.strip()}'."
            )
        if attendance_date < joining_date:
            raise ValueError(
                f"Cannot record attendance on {attendance_date} before employee joining date ({joining_date})."
            )

        cursor.execute(
            """
            INSERT INTO attendance (employee_id, attendance_date, status)
            VALUES (%s, %s, %s)
            """,
            (emp_id, attendance_date, status),
        )
        new_id = cursor.lastrowid
        log_attendance_action(
            conn,
            attendance_id=new_id,
            employee_id=emp_id,
            attendance_date=attendance_date,
            action_type="CREATE",
            new_status=status,
            user_id=user_id,
            username=username,
        )
        conn.commit()
        return new_id
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
    reason: str | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> None:
    """Update status of an existing attendance record with audit trail."""
    from src.audit import log_attendance_action

    if status == "Holiday":
        raise ValueError(
            "Individual attendance cannot be updated to 'Holiday'. Holidays must be recorded organization-wide."
        )
    if status not in ALLOWED_DAILY_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(ALLOWED_DAILY_STATUSES)}"
        )
    if attendance_date.weekday() >= 5:
        raise ValueError(
            f"Attendance cannot be recorded on weekends ({attendance_date})."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_id, is_active, joining_date FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        emp = cursor.fetchone()
        if not emp:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")
        emp_id, is_active, joining_date = emp
        if not is_active:
            raise ValueError(
                f"Cannot update attendance for inactive employee '{employee_code.strip()}'."
            )
        if attendance_date < joining_date:
            raise ValueError(
                f"Cannot update attendance on {attendance_date} before employee joining date ({joining_date})."
            )

        cursor.execute(
            "SELECT attendance_id, status FROM attendance WHERE employee_id = %s AND attendance_date = %s",
            (emp_id, attendance_date),
        )
        existing_row = cursor.fetchone()
        if not existing_row:
            raise ValueError(
                f"No existing attendance row found for employee '{employee_code}' on {attendance_date}."
            )
        att_id, prev_status = existing_row

        cursor.execute(
            """
            UPDATE attendance
            SET status = %s
            WHERE attendance_id = %s
            """,
            (status, att_id),
        )

        effective_reason = reason.strip() if reason and reason.strip() else "Attendance correction"
        log_attendance_action(
            conn,
            attendance_id=att_id,
            employee_id=emp_id,
            attendance_date=attendance_date,
            action_type="CORRECT",
            previous_status=prev_status,
            new_status=status,
            reason=effective_reason,
            user_id=user_id,
            username=username,
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
    department: str | None = None,
    status: str | None = None,
    search_query: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    order_asc: bool = False,
) -> list[dict]:
    """Retrieve attendance records with optional filters and bounded pagination."""
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

        dept_val = department.strip() if department and department.strip() else None
        status_val = status.strip() if status and status.strip() else None
        code_val = employee_code.strip() if employee_code is not None else None
        search_val = f"%{search_query.strip()}%" if search_query and search_query.strip() else None

        order_clause = "ORDER BY a.attendance_date ASC, e.employee_code ASC" if order_asc else "ORDER BY a.attendance_date DESC, e.employee_code ASC"

        sql = f"""
            SELECT a.attendance_id, a.employee_id, e.employee_code, e.employee_name, e.department, a.attendance_date, a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE (%s IS NULL OR e.employee_code = %s)
              AND (%s IS NULL OR a.attendance_date >= %s)
              AND (%s IS NULL OR a.attendance_date <= %s)
              AND (%s IS NULL OR e.department = %s)
              AND (%s IS NULL OR a.status = %s)
              AND (%s IS NULL OR (e.employee_code LIKE %s OR e.employee_name LIKE %s))
            {order_clause}
        """
        params = [
            code_val, code_val,
            start_date, start_date,
            end_date, end_date,
            dept_val, dept_val,
            status_val, status_val,
            search_val, search_val, search_val,
        ]

        if limit is not None:
            sql += f" LIMIT {int(limit)}"
            if offset is not None:
                sql += f" OFFSET {int(offset)}"

        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()


def count_attendance(
    conn: MySQLConnectionAbstract,
    employee_code: str | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    department: str | None = None,
    status: str | None = None,
    search_query: str | None = None,
) -> int:
    """Return count of attendance records matching given filters."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    cursor = conn.cursor()
    try:
        dept_val = department.strip() if department and department.strip() else None
        status_val = status.strip() if status and status.strip() else None
        code_val = employee_code.strip() if employee_code is not None else None
        search_val = f"%{search_query.strip()}%" if search_query and search_query.strip() else None

        sql = """
            SELECT COUNT(*)
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE (%s IS NULL OR e.employee_code = %s)
              AND (%s IS NULL OR a.attendance_date >= %s)
              AND (%s IS NULL OR a.attendance_date <= %s)
              AND (%s IS NULL OR e.department = %s)
              AND (%s IS NULL OR a.status = %s)
              AND (%s IS NULL OR (e.employee_code LIKE %s OR e.employee_name LIKE %s))
        """
        params = [
            code_val, code_val,
            start_date, start_date,
            end_date, end_date,
            dept_val, dept_val,
            status_val, status_val,
            search_val, search_val, search_val,
        ]

        cursor.execute(sql, tuple(params))
        (total,) = cursor.fetchone()
        return total
    finally:
        cursor.close()


def record_holiday(
    conn: MySQLConnectionAbstract,
    holiday_date: datetime.date,
    user_id: int | None = None,
    username: str | None = None,
) -> int:
    """Insert a Holiday row for every active employee on holiday_date in one transaction."""
    from src.audit import log_attendance_action

    if holiday_date.weekday() >= 5:
        raise ValueError(
            f"Holidays cannot be recorded on weekends ({holiday_date})."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT employee_id FROM employees
            WHERE is_active = TRUE AND joining_date <= %s
            ORDER BY employee_id
            """,
            (holiday_date,),
        )
        active_employees = [row[0] for row in cursor.fetchall()]
        if not active_employees:
            return 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE e.is_active = TRUE AND e.joining_date <= %s AND a.attendance_date = %s
            """,
            (holiday_date, holiday_date),
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

        for emp_id in active_employees:
            log_attendance_action(
                conn,
                employee_id=emp_id,
                attendance_date=holiday_date,
                action_type="CREATE",
                new_status="Holiday",
                reason="Organization Holiday",
                user_id=user_id,
                username=username,
            )

        conn.commit()
        return len(holiday_rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()

