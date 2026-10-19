"""Seed script to populate sample employees and September 2026 attendance."""

import datetime
from pathlib import Path
import sys

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db import get_connection

EMPLOYEES_DATA = [
    ("E001", "Asha Rao", "Engineering", True, datetime.date(2026, 1, 15)),
    ("E002", "Ravi Kumar", "Engineering", True, datetime.date(2026, 2, 1)),
    ("E003", "Meera Nair", "Sales", True, datetime.date(2026, 3, 10)),
    ("E004", "Karan Shah", "Sales", True, datetime.date(2026, 4, 1)),
    ("E005", "Divya Menon", "HR", True, datetime.date(2026, 5, 1)),
    ("E006", "Sample Newjoiner", "HR", True, datetime.date(2026, 9, 1)),
]

ATTENDANCE_COUNTS = {
    "E001": {"Present": 21, "Absent": 0, "Leave": 0},
    "E002": {"Present": 18, "Absent": 2, "Leave": 1},
    "E003": {"Present": 14, "Absent": 4, "Leave": 3},
    "E004": {"Present": 20, "Absent": 0, "Leave": 1},
    "E005": {"Present": 7, "Absent": 14, "Leave": 0},
    "E006": {"Present": 0, "Absent": 0, "Leave": 0},
}


def get_september_2026_dates() -> tuple[list[datetime.date], datetime.date]:
    """Generate the 21 normal weekdays and 1 holiday date for September 2026."""
    holiday = datetime.date(2026, 9, 14)
    normal_weekdays: list[datetime.date] = []
    for day in range(1, 31):
        current_date = datetime.date(2026, 9, day)
        if current_date.weekday() < 5 and current_date != holiday:
            normal_weekdays.append(current_date)
    return normal_weekdays, holiday


def build_attendance_rows(
    emp_code_to_id: dict[str, int],
) -> list[tuple[int, datetime.date, str]]:
    """Construct attendance rows for all employees following business rules."""
    normal_weekdays, holiday = get_september_2026_dates()
    rows: list[tuple[int, datetime.date, str]] = []

    for code, counts in ATTENDANCE_COUNTS.items():
        emp_id = emp_code_to_id[code]
        # Always insert Holiday row for every active employee
        rows.append((emp_id, holiday, "Holiday"))

        # Build normal day statuses in date order: Present, Absent, Leave
        statuses: list[str] = (
            ["Present"] * counts["Present"]
            + ["Absent"] * counts["Absent"]
            + ["Leave"] * counts["Leave"]
        )

        for date_val, status in zip(normal_weekdays, statuses):
            rows.append((emp_id, date_val, status))

    return rows


def seed_database(database_name: str | None = None) -> None:
    """Seed employees and attendance records into the database inside a single transaction."""
    conn = get_connection(database_name)
    try:
        cursor = conn.cursor()

        # Refuse to run if employees table already has rows
        cursor.execute("SELECT COUNT(*) FROM employees")
        (count,) = cursor.fetchone()
        if count > 0:
            print("Database already contains employee rows. Seeding aborted.")
            cursor.close()
            return

        # Insert employees using parameterized SQL
        insert_emp_query = """
            INSERT INTO employees (employee_code, employee_name, department, is_active, joining_date)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_emp_query, EMPLOYEES_DATA)

        # Retrieve inserted employee IDs
        cursor.execute("SELECT employee_code, employee_id FROM employees")
        emp_code_to_id = {code: emp_id for code, emp_id in cursor.fetchall()}

        # Build and insert attendance records
        attendance_rows = build_attendance_rows(emp_code_to_id)
        insert_att_query = """
            INSERT INTO attendance (employee_id, attendance_date, status)
            VALUES (%s, %s, %s)
        """
        cursor.executemany(insert_att_query, attendance_rows)

        conn.commit()
        print(
            f"Seeding completed successfully: {len(EMPLOYEES_DATA)} employees and {len(attendance_rows)} attendance records inserted."
        )
        cursor.close()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()


if __name__ == "__main__":
    target_database = sys.argv[1] if len(sys.argv) > 1 else None
    seed_database(target_database)
