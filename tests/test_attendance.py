"""Tests for attendance recording and holiday operations."""

import datetime
import pytest
from src.attendance import (
    AttendanceConflictError,
    check_department_attendance_conflicts,
    get_attendance,
    record_attendance,
    record_department_attendance,
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


def test_attendance_before_joining_date_refused(conn):
    """Recording attendance earlier than employee's joining date raises ValueError."""
    add_employee(conn, "E015", "Late Joiner", "Engineering", joining_date=datetime.date(2026, 9, 15))

    with pytest.raises(ValueError, match="before employee joining date"):
        record_attendance(conn, "E015", datetime.date(2026, 9, 10), "Present")

    # On or after joining date succeeds
    att_id = record_attendance(conn, "E015", datetime.date(2026, 9, 15), "Present")
    assert isinstance(att_id, int)


def test_update_attendance_before_joining_date_refused(conn):
    """Updating attendance earlier than employee's joining date raises ValueError."""
    add_employee(conn, "E016", "Mid Joiner", "Engineering", joining_date=datetime.date(2026, 9, 10))
    record_attendance(conn, "E016", datetime.date(2026, 9, 10), "Present")

    # Try to update for date before joining date
    with pytest.raises(ValueError, match="before employee joining date"):
        update_attendance(conn, "E016", datetime.date(2026, 9, 4), "Absent")


def test_individual_holiday_status_refused(conn):
    """record_attendance refuses individual status 'Holiday'."""
    add_employee(conn, "E017", "Holiday Tester", "Engineering")

    with pytest.raises(ValueError, match="Individual attendance cannot be marked as 'Holiday'"):
        record_attendance(conn, "E017", datetime.date(2026, 9, 1), "Holiday")


def test_update_attendance_holiday_status_refused(conn):
    """update_attendance refuses updating status to 'Holiday'."""
    add_employee(conn, "E018", "Holiday Updater", "Engineering")
    record_attendance(conn, "E018", datetime.date(2026, 9, 1), "Present")

    with pytest.raises(ValueError, match="Individual attendance cannot be updated to 'Holiday'"):
        update_attendance(conn, "E018", datetime.date(2026, 9, 1), "Holiday")


def test_update_attendance_inactive_employee_refused(conn):
    """update_attendance refuses modifying records for inactive employees."""
    add_employee(conn, "E019", "Deactivated Tester", "Engineering")
    record_attendance(conn, "E019", datetime.date(2026, 9, 1), "Present")
    deactivate_employee(conn, "E019")

    with pytest.raises(ValueError, match="Cannot update attendance for inactive employee"):
        update_attendance(conn, "E019", datetime.date(2026, 9, 1), "Absent")


def test_record_holiday_excludes_pre_joining_employees(conn):
    """record_holiday creates rows only for active employees joined on or before holiday date."""
    add_employee(conn, "E020", "Senior Member", "Engineering", joining_date="2026-09-01")
    add_employee(conn, "E021", "Future Joiner", "Engineering", joining_date="2026-09-20")

    holiday_date = datetime.date(2026, 9, 14)
    count = record_holiday(conn, holiday_date)
    assert count == 1

    records = get_attendance(conn, start_date=holiday_date, end_date=holiday_date)
    assert len(records) == 1
    assert records[0]["employee_code"] == "E020"


def test_record_department_attendance_success(conn):
    """Department bulk attendance successfully inserts all roster members atomically."""
    add_employee(conn, "E030", "Dev One", "Engineering", joining_date="2026-09-01")
    add_employee(conn, "E031", "Dev Two", "Engineering", joining_date="2026-09-01")
    add_employee(conn, "E032", "Dev Three", "Engineering", joining_date="2026-09-01")

    att_date = datetime.date(2026, 9, 8)
    entries = [
        {"employee_code": "E030", "status": "Present"},
        {"employee_code": "E031", "status": "Absent"},
        {"employee_code": "E032", "status": "Leave"},
    ]
    res = record_department_attendance(conn, "Engineering", att_date, entries)
    assert res["total_records"] == 3
    assert res["present_count"] == 1
    assert res["absent_count"] == 1
    assert res["leave_count"] == 1
    assert res["department"] == "Engineering"

    records = get_attendance(conn, start_date=att_date, end_date=att_date)
    assert len(records) == 3
    rec_map = {r["employee_code"]: r["status"] for r in records}
    assert rec_map == {"E030": "Present", "E031": "Absent", "E032": "Leave"}


def test_record_department_attendance_weekend_refused(conn):
    """Department bulk attendance refuses recording on weekends."""
    add_employee(conn, "E030", "Dev One", "Engineering")
    sat_date = datetime.date(2026, 9, 5)
    entries = [{"employee_code": "E030", "status": "Present"}]

    with pytest.raises(ValueError, match="cannot be recorded on weekends"):
        record_department_attendance(conn, "Engineering", sat_date, entries)


def test_record_department_attendance_invalid_or_nonexistent_department(conn):
    """Department bulk attendance rejects blank or non-existent departments."""
    att_date = datetime.date(2026, 9, 8)
    with pytest.raises(ValueError, match="Department cannot be blank"):
        record_department_attendance(conn, "  ", att_date, [])

    with pytest.raises(ValueError, match="Department 'Finance' does not exist"):
        record_department_attendance(conn, "Finance", att_date, [])


def test_record_department_attendance_pre_joining_and_inactive_filtered(conn):
    """Department bulk attendance considers only active employees joined on or before date."""
    add_employee(conn, "E033", "Senior Dev", "Operations", joining_date="2026-09-01")
    add_employee(conn, "E034", "Future Dev", "Operations", joining_date="2026-09-15")
    add_employee(conn, "E035", "Left Dev", "Operations", joining_date="2026-09-01")
    deactivate_employee(conn, "E035")

    att_date = datetime.date(2026, 9, 8)

    # Trying to include future or inactive employee raises ValueError
    bad_entries = [
        {"employee_code": "E033", "status": "Present"},
        {"employee_code": "E034", "status": "Present"},
    ]
    with pytest.raises(ValueError, match="is not an active eligible member"):
        record_department_attendance(conn, "Operations", att_date, bad_entries)

    # Only eligible active employee joined before date succeeds
    good_entries = [{"employee_code": "E033", "status": "Present"}]
    res = record_department_attendance(conn, "Operations", att_date, good_entries)
    assert res["total_records"] == 1


def test_record_department_attendance_duplicate_and_missing_entries(conn):
    """Department bulk attendance requires every eligible employee exactly once."""
    add_employee(conn, "E036", "Emp A", "HR", joining_date="2026-09-01")
    add_employee(conn, "E037", "Emp B", "HR", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    # Missing E037
    with pytest.raises(ValueError, match="Missing attendance entries"):
        record_department_attendance(
            conn, "HR", att_date, [{"employee_code": "E036", "status": "Present"}]
        )

    # Duplicate E036
    with pytest.raises(ValueError, match="Duplicate entry for employee 'E036'"):
        record_department_attendance(
            conn,
            "HR",
            att_date,
            [
                {"employee_code": "E036", "status": "Present"},
                {"employee_code": "E036", "status": "Absent"},
            ],
        )


def test_record_department_attendance_invalid_status_refused(conn):
    """Department bulk attendance refuses 'Holiday' and invalid status strings."""
    add_employee(conn, "E038", "Emp Status", "Legal", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    with pytest.raises(ValueError, match="Individual attendance cannot be marked as 'Holiday'"):
        record_department_attendance(
            conn, "Legal", att_date, [{"employee_code": "E038", "status": "Holiday"}]
        )

    with pytest.raises(ValueError, match="Invalid status 'Sick'"):
        record_department_attendance(
            conn, "Legal", att_date, [{"employee_code": "E038", "status": "Sick"}]
        )


def test_record_department_attendance_atomic_conflict_rollback(conn):
    """If any employee already has attendance on the date, entire batch is rolled back."""
    add_employee(conn, "E040", "First Member", "QA", joining_date="2026-09-01")
    add_employee(conn, "E041", "Second Member", "QA", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    # Record attendance for E040 first
    record_attendance(conn, "E040", att_date, "Present")

    entries = [
        {"employee_code": "E040", "status": "Present"},
        {"employee_code": "E041", "status": "Present"},
    ]
    with pytest.raises(AttendanceConflictError) as exc_info:
        record_department_attendance(conn, "QA", att_date, entries)

    assert "Attendance already recorded for 1 employee(s)" in str(exc_info.value)
    assert exc_info.value.conflicts[0]["employee_code"] == "E040"

    # Verify atomic rollback: E041 has NO row recorded
    records = get_attendance(conn, employee_code="E041", start_date=att_date, end_date=att_date)
    assert len(records) == 0


def test_check_department_attendance_conflicts(conn):
    """check_department_attendance_conflicts returns active conflicting employees."""
    add_employee(conn, "E042", "Conflicting Emp", "Design", joining_date="2026-09-01")
    add_employee(conn, "E043", "Free Emp", "Design", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    conflicts_before = check_department_attendance_conflicts(conn, "Design", att_date)
    assert len(conflicts_before) == 0

    record_attendance(conn, "E042", att_date, "Present")

    conflicts_after = check_department_attendance_conflicts(conn, "Design", att_date)
    assert len(conflicts_after) == 1
    assert conflicts_after[0]["employee_code"] == "E042"
    assert conflicts_after[0]["employee_name"] == "Conflicting Emp"


def test_get_attendance_department_filtering(conn):
    """get_attendance supports filtering by department."""
    add_employee(conn, "E044", "Sales Rep", "Sales", joining_date="2026-09-01")
    add_employee(conn, "E045", "Dev Guy", "Engineering", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    record_attendance(conn, "E044", att_date, "Present")
    record_attendance(conn, "E045", att_date, "Present")

    sales_rows = get_attendance(conn, department="Sales")
    assert len(sales_rows) == 1
    assert sales_rows[0]["employee_code"] == "E044"
    assert sales_rows[0]["department"] == "Sales"
    assert sales_rows[0]["employee_name"] == "Sales Rep"


