"""Tests for attendance recording and holiday operations."""

import datetime
import pytest
from src.attendance import (
    get_attendance,
    record_attendance,
    record_holiday,
    update_attendance,
)
from src.employees import add_employee, deactivate_employee


def test_record_then_get(conn):
    """Record then get returns the row."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    att_id = record_attendance(
        conn, "E001", datetime.date(2026, 9, 1), "Present"
    )
    assert isinstance(att_id, int)

    rows = get_attendance(conn, "E001")
    assert len(rows) == 1
    assert rows[0]["employee_code"] == "E001"
    assert rows[0]["attendance_date"] == datetime.date(2026, 9, 1)
    assert rows[0]["status"] == "Present"


def test_duplicate_record_refused(conn):
    """A second record for the same employee and date is refused and only 1 row exists."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")

    with pytest.raises(ValueError):
        record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")

    rows = get_attendance(conn, "E001")
    assert len(rows) == 1


def test_invalid_status_refused(conn):
    """Status 'Sick' is refused and no row exists."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")

    with pytest.raises(ValueError):
        record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Sick")

    rows = get_attendance(conn, "E001")
    assert len(rows) == 0


def test_nonexistent_and_inactive_employee_refused(conn):
    """Nonexistent employee refused; inactive employee refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")

    with pytest.raises(ValueError):
        record_attendance(
            conn, "E999", datetime.date(2026, 9, 1), "Present"
        )

    deactivate_employee(conn, "E001")
    with pytest.raises(ValueError):
        record_attendance(
            conn, "E001", datetime.date(2026, 9, 1), "Present"
        )


def test_saturday_refused(conn):
    """Saturday 2026-09-05 refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")

    with pytest.raises(ValueError):
        record_attendance(
            conn, "E001", datetime.date(2026, 9, 5), "Present"
        )


def test_month_end_and_year_end_recorded(conn):
    """2026-12-31 (Thursday, year end) and 2026-09-30 (month end) can be recorded."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")

    id_month_end = record_attendance(
        conn, "E001", datetime.date(2026, 9, 30), "Present"
    )
    id_year_end = record_attendance(
        conn, "E001", datetime.date(2026, 12, 31), "Leave"
    )

    assert isinstance(id_month_end, int)
    assert isinstance(id_year_end, int)

    rows = get_attendance(conn, "E001")
    assert len(rows) == 2


def test_update_attendance(conn):
    """update_attendance changes Present to Absent; update on a date with no row is refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")

    update_attendance(conn, "E001", datetime.date(2026, 9, 1), "Absent")
    rows = get_attendance(conn, "E001")
    assert len(rows) == 1
    assert rows[0]["status"] == "Absent"

    with pytest.raises(ValueError):
        update_attendance(conn, "E001", datetime.date(2026, 9, 2), "Present")


def test_get_attendance_filtering(conn):
    """Rows on 2026-09-01, 02, 03: range 02 to 03 returns exactly 2; employee filter works; start after end refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")

    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 3), "Present")
    record_attendance(conn, "E002", datetime.date(2026, 9, 2), "Present")

    # Range 02 to 03 for E001 returns exactly 2
    range_rows = get_attendance(
        conn,
        employee_code="E001",
        start_date=datetime.date(2026, 9, 2),
        end_date=datetime.date(2026, 9, 3),
    )
    assert len(range_rows) == 2

    # Filtering by employee returns only that employee's rows
    e002_rows = get_attendance(conn, employee_code="E002")
    assert len(e002_rows) == 1
    assert e002_rows[0]["employee_code"] == "E002"

    # start_date after end_date is refused
    with pytest.raises(ValueError):
        get_attendance(
            conn,
            start_date=datetime.date(2026, 9, 3),
            end_date=datetime.date(2026, 9, 2),
        )


def test_record_holiday_active_only(conn):
    """record_holiday with 2 active and 1 inactive employee inserts exactly 2 rows, returns 2, and inactive gets none."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")
    add_employee(conn, "E003", "Meera Nair", "Sales")
    deactivate_employee(conn, "E003")

    holiday_date = datetime.date(2026, 9, 14)
    inserted = record_holiday(conn, holiday_date)
    assert inserted == 2

    rows = get_attendance(conn)
    assert len(rows) == 2
    codes = {r["employee_code"] for r in rows}
    assert codes == {"E001", "E002"}
    assert all(r["status"] == "Holiday" for r in rows)


def test_record_holiday_conflict_refused(conn):
    """record_holiday refused when one active employee already has a Present row on that date; table has no new rows."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")

    holiday_date = datetime.date(2026, 9, 14)
    record_attendance(conn, "E001", holiday_date, "Present")

    with pytest.raises(ValueError):
        record_holiday(conn, holiday_date)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM attendance")
    assert cur.fetchone()[0] == 1  # Only the original Present row exists
    cur.close()


def test_record_holiday_weekend_refused(conn):
    """record_holiday on a Saturday is refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    saturday = datetime.date(2026, 9, 5)

    with pytest.raises(ValueError):
        record_holiday(conn, saturday)
