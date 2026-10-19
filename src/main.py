"""Command-line menu interface for employee attendance analysis system."""

import datetime
from pathlib import Path
import sys
from typing import Callable
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    load_attendance_df,
)
from src.attendance import (
    ALLOWED_DAILY_STATUSES,
    VALID_STATUSES,
    get_attendance,
    record_attendance,
    record_department_attendance,
    record_holiday,
    update_attendance,
)
from src.db import get_connection
from src.employees import (
    add_employee,
    deactivate_employee,
    get_department_employees,
    list_employees,
    search_employees,
    update_employee,
)
from src.reports import (
    export_charts,
    format_absenteeism_report,
    format_department_report,
    format_employee_report,
    generate_monthly_report,
)


def _parse_date(date_str: str) -> datetime.date:
    """Parse an ISO format date string into a date object."""
    try:
        return datetime.date.fromisoformat(date_str.strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid date '{date_str}'. Expected format: YYYY-MM-DD."
        ) from exc


def _parse_optional_date(date_str: str) -> datetime.date | None:
    """Parse an optional date string, returning None for empty strings."""
    stripped = date_str.strip()
    if not stripped:
        return None
    return _parse_date(stripped)


def _handle_add_employee(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code = input_fn("Enter employee code: ")
    name = input_fn("Enter employee name: ")
    dept = input_fn("Enter department: ")
    emp_id = add_employee(conn, code, name, dept)
    output_fn(f"Employee added with ID: {emp_id}")


def _handle_list_employees(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    inc_input = input_fn("Include inactive employees? (y/n): ").strip().lower()
    include_inactive = inc_input == "y"
    emps = list_employees(conn, include_inactive=include_inactive)
    if not emps:
        output_fn("No records found.")
    else:
        for e in emps:
            status_str = "Active" if e["is_active"] else "Inactive"
            output_fn(
                f"{e['employee_code']} | {e['employee_name']} | {e['department']} | {status_str}"
            )


def _handle_search_employees(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    text = input_fn("Enter search text: ")
    emps = search_employees(conn, text)
    if not emps:
        output_fn("No records found.")
    else:
        for e in emps:
            status_str = "Active" if e["is_active"] else "Inactive"
            output_fn(
                f"{e['employee_code']} | {e['employee_name']} | {e['department']} | {status_str}"
            )


def _handle_update_employee(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code = input_fn("Enter employee code: ")
    name = input_fn("Enter new name (blank keeps): ")
    dept = input_fn("Enter new department (blank keeps): ")
    new_name = name.strip() if name.strip() else None
    new_dept = dept.strip() if dept.strip() else None
    update_employee(conn, code, employee_name=new_name, department=new_dept)
    output_fn("Employee updated successfully.")


def _handle_deactivate_employee(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code = input_fn("Enter employee code: ")
    confirm = input_fn("Type YES to confirm: ")
    if confirm != "YES":
        output_fn("Cancelled.")
    else:
        deactivate_employee(conn, code)
        output_fn(f"Employee {code} deactivated.")


def _handle_record_attendance(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code = input_fn("Enter employee code: ")
    date_str = input_fn("Enter date (YYYY-MM-DD): ")
    att_date = _parse_date(date_str)
    status_prompt = f"Enter status ({', '.join(VALID_STATUSES)}): "
    status = input_fn(status_prompt).strip().capitalize()
    record_attendance(conn, code, att_date, status)
    output_fn("Attendance recorded successfully.")


def _handle_correct_attendance(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code = input_fn("Enter employee code: ")
    date_str = input_fn("Enter date (YYYY-MM-DD): ")
    att_date = _parse_date(date_str)
    status_prompt = f"Enter new status ({', '.join(VALID_STATUSES)}): "
    status = input_fn(status_prompt).strip().capitalize()
    update_attendance(conn, code, att_date, status)
    output_fn("Attendance corrected successfully.")


def _handle_view_attendance(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    code_input = input_fn(
        "Enter employee code (blank = all employees): "
    ).strip()
    code = code_input if code_input else None
    start_str = input_fn("Enter start date (blank): ")
    end_str = input_fn("Enter end date (blank): ")
    start_date = _parse_optional_date(start_str)
    end_date = _parse_optional_date(end_str)

    if start_date is not None and end_date is not None and start_date > end_date:
        output_fn("Error: Start date cannot be after end date.")
        return

    records = get_attendance(
        conn, employee_code=code, start_date=start_date, end_date=end_date
    )
    if not records:
        output_fn("No records found.")
    else:
        for r in records:
            d = (
                r["attendance_date"].isoformat()
                if hasattr(r["attendance_date"], "isoformat")
                else str(r["attendance_date"])
            )
            output_fn(f"{d} | {r['employee_code']} | {r['status']}")


def _handle_record_holiday(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    date_str = input_fn("Enter date (YYYY-MM-DD): ")
    holiday_date = _parse_date(date_str)
    count = record_holiday(conn, holiday_date)
    output_fn(f"Recorded holiday for {count} active employee(s).")


def _handle_employee_summary(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    start_str = input_fn("Enter start date (blank): ")
    end_str = input_fn("Enter end date (blank): ")
    start_date = _parse_optional_date(start_str)
    end_date = _parse_optional_date(end_str)

    if start_date is not None and end_date is not None and start_date > end_date:
        output_fn("Error: Start date cannot be after end date.")
        return

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    output_fn(format_employee_report(summary_df))


def _handle_department_summary(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    start_str = input_fn("Enter start date (blank): ")
    end_str = input_fn("Enter end date (blank): ")
    start_date = _parse_optional_date(start_str)
    end_date = _parse_optional_date(end_str)

    if start_date is not None and end_date is not None and start_date > end_date:
        output_fn("Error: Start date cannot be after end date.")
        return

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = department_summary(df)
    output_fn(format_department_report(summary_df))


def _handle_absenteeism_ranking(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    start_str = input_fn("Enter start date (blank): ")
    end_str = input_fn("Enter end date (blank): ")
    start_date = _parse_optional_date(start_str)
    end_date = _parse_optional_date(end_str)

    if start_date is not None and end_date is not None and start_date > end_date:
        output_fn("Error: Start date cannot be after end date.")
        return

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    ranking_df = absenteeism_ranking(summary_df)
    output_fn(format_absenteeism_report(ranking_df))


def _handle_monthly_report(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    year_str = input_fn("Enter year (e.g. 2026): ")
    month_str = input_fn("Enter month (1-12): ")
    try:
        year = int(year_str.strip())
        month = int(month_str.strip())
    except (ValueError, TypeError) as exc:
        raise ValueError("Year and month must be numbers.") from exc
    report = generate_monthly_report(conn, year, month)
    output_fn(report)


def _handle_export_charts(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    year_str = input_fn("Enter year (e.g. 2026): ")
    month_str = input_fn("Enter month (1-12): ")
    try:
        year = int(year_str.strip())
        month = int(month_str.strip())
    except (ValueError, TypeError) as exc:
        raise ValueError("Year and month must be numbers.") from exc
    paths = export_charts(conn, year, month)
    output_fn(f"Exported charts:\n- {paths[0]}\n- {paths[1]}")


def _handle_record_department_attendance(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> None:
    dept = input_fn("Enter department: ").strip()
    date_str = input_fn("Enter date (YYYY-MM-DD): ").strip()
    att_date = _parse_date(date_str)

    eligible = get_department_employees(
        conn, dept, active_only=True, eligible_as_of=att_date
    )
    if not eligible:
        output_fn(
            f"No eligible active employees found in department '{dept}' on {att_date}."
        )
        return

    output_fn(f"Found {len(eligible)} eligible employee(s) in {dept}:")
    for emp in eligible:
        output_fn(
            f"  {emp['employee_code']} - {emp['employee_name']} (Joined: {emp['joining_date']})"
        )

    mark_all = input_fn("Mark all as Present? (y/n): ").strip().lower()
    entries = []
    if mark_all == "y":
        for emp in eligible:
            entries.append(
                {"employee_code": emp["employee_code"], "status": "Present"}
            )
    else:
        for emp in eligible:
            st = input_fn(
                f"Enter status for {emp['employee_code']} ({', '.join(ALLOWED_DAILY_STATUSES)}) [Present]: "
            ).strip().capitalize()
            if not st:
                st = "Present"
            entries.append({"employee_code": emp["employee_code"], "status": st})

    res = record_department_attendance(conn, dept, att_date, entries)
    output_fn(
        f"Recorded attendance for {res['total_records']} employee(s) in {dept} on {att_date} "
        f"({res['present_count']} Present, {res['absent_count']} Absent, {res['leave_count']} Leave)."
    )


HANDLERS = {
    "1": _handle_add_employee,
    "2": _handle_list_employees,
    "3": _handle_search_employees,
    "4": _handle_update_employee,
    "5": _handle_deactivate_employee,
    "6": _handle_record_attendance,
    "7": _handle_correct_attendance,
    "8": _handle_view_attendance,
    "9": _handle_record_holiday,
    "10": _handle_employee_summary,
    "11": _handle_department_summary,
    "12": _handle_absenteeism_ranking,
    "13": _handle_monthly_report,
    "14": _handle_export_charts,
    "15": _handle_record_department_attendance,
}


def run_menu(
    conn: MySQLConnectionAbstract,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Execute the interactive command-line menu loop until user exits or input terminates."""
    while True:
        output_fn("\n=== Employee Attendance Analysis System ===")
        output_fn("1. Add employee")
        output_fn("2. List employees")
        output_fn("3. Search employees")
        output_fn("4. Update employee")
        output_fn("5. Deactivate employee")
        output_fn("6. Record attendance")
        output_fn("7. Correct attendance")
        output_fn("8. View attendance")
        output_fn("9. Record holiday for all active employees")
        output_fn("10. Employee summary")
        output_fn("11. Department summary")
        output_fn("12. Absenteeism ranking")
        output_fn("13. Monthly report")
        output_fn("14. Export charts")
        output_fn("15. Record department attendance")
        output_fn("0. Exit")

        try:
            choice = input_fn("Enter choice (0-15): ").strip()
        except EOFError:
            break

        if choice == "0":
            break

        handler = HANDLERS.get(choice)
        if handler is not None:
            try:
                handler(conn, input_fn, output_fn)
            except ValueError as exc:
                output_fn(f"Error: {exc}")
            except EOFError:
                break
        else:
            output_fn("Invalid choice")


def main() -> None:
    """Open database connection and start command-line menu application."""
    conn = None
    try:
        conn = get_connection()
        run_menu(conn)
    except mysql.connector.Error as err:
        print(f"Database error: {err.msg}")
        sys.exit(1)
    except ConnectionError as err:
        print(f"Database error: {err}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
