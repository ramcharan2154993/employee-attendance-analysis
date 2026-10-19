"""Tests for report formatting, chart generation, and export."""

import datetime
from pathlib import Path
import pandas as pd
import pytest
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    monthly_summary,
)
from src.attendance import get_attendance, record_attendance, record_holiday
from src.employees import add_employee
from src.reports import (
    export_charts,
    format_absenteeism_report,
    format_department_report,
    format_employee_report,
    generate_monthly_report,
)
from src.visualizations import (
    save_absenteeism_chart,
    save_monthly_attendance_chart,
)


def _create_sample_df() -> pd.DataFrame:
    """Helper creating hand-built test DataFrame with known attendance counts."""
    rows = []
    # E001 (Engineering): 15 Present, 3 Absent, 2 Leave, 2 Holiday
    for _ in range(15):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 1),
            "status": "Present",
        })
    for _ in range(3):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 2),
            "status": "Absent",
        })
    for _ in range(2):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 3),
            "status": "Leave",
        })
    for _ in range(2):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 14),
            "status": "Holiday",
        })

    # E002 (Engineering): 5 Present, 5 Absent
    for _ in range(5):
        rows.append({
            "employee_code": "E002",
            "employee_name": "Ravi Kumar",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 1),
            "status": "Present",
        })
    for _ in range(5):
        rows.append({
            "employee_code": "E002",
            "employee_name": "Ravi Kumar",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 2),
            "status": "Absent",
        })

    # E003 (HR): 1 Holiday only
    rows.append({
        "employee_code": "E003",
        "employee_name": "Divya Menon",
        "department": "HR",
        "is_active": True,
        "attendance_date": datetime.date(2026, 9, 14),
        "status": "Holiday",
    })

    return pd.DataFrame(rows)


def test_pure_format_employee_report():
    """format_employee_report text contains 75.00% & 15.00% for E001, 50.00% for E002, and N/A for E003."""
    df = _create_sample_df()
    es = employee_summary(df)
    report = format_employee_report(es)

    e1_line = [line for line in report.splitlines() if "E001" in line][0]
    assert "75.00%" in e1_line
    assert "15.00%" in e1_line

    e2_line = [line for line in report.splitlines() if "E002" in line][0]
    assert "50.00%" in e2_line

    e3_line = [line for line in report.splitlines() if "E003" in line][0]
    assert "N/A" in e3_line


def test_pure_format_department_report():
    """format_department_report: Engineering line contains 66.67% and NOT 62.50%."""
    df = _create_sample_df()
    dept = department_summary(df)
    report = format_department_report(dept)

    eng_line = [line for line in report.splitlines() if "Engineering" in line][0]
    assert "66.67%" in eng_line
    assert "62.50%" not in eng_line


def test_pure_format_absenteeism_report():
    """format_absenteeism_report lists E002 before E001, and E003 last."""
    df = _create_sample_df()
    es = employee_summary(df)
    ranking = absenteeism_ranking(es)
    report = format_absenteeism_report(ranking)

    lines = report.splitlines()
    e2_idx = next(i for i, line in enumerate(lines) if "E002" in line)
    e1_idx = next(i for i, line in enumerate(lines) if "E001" in line)
    e3_idx = next(i for i, line in enumerate(lines) if "E003" in line)

    assert e2_idx < e1_idx < e3_idx


def test_pure_format_reports_empty_dataframe():
    """Empty DataFrames passed to format functions do not raise errors."""
    empty_df = pd.DataFrame()
    assert isinstance(format_employee_report(empty_df), str)
    assert isinstance(format_department_report(empty_df), str)
    assert isinstance(format_absenteeism_report(empty_df), str)


def test_chart_functions_create_valid_png(tmp_path):
    """Both chart functions save a file that exists, > 0 bytes, and starts with b'\\x89PNG'."""
    df = _create_sample_df()
    ranking = absenteeism_ranking(employee_summary(df))
    monthly = monthly_summary(df)

    # Save to a subfolder that does not exist yet to test folder creation
    chart_dir = tmp_path / "new_charts_dir"
    chart1 = save_absenteeism_chart(
        ranking, chart_dir / "absenteeism.png", "Absenteeism"
    )
    chart2 = save_monthly_attendance_chart(
        monthly, chart_dir / "monthly.png", "Monthly"
    )

    for path in (chart1, chart2):
        assert path.exists()
        assert path.stat().st_size > 0
        with open(path, "rb") as f:
            header = f.read(4)
            assert header == b"\x89PNG"


def test_chart_functions_with_empty_dataframe(tmp_path):
    """Both chart functions work with empty DataFrames (valid PNG, no error)."""
    empty_df = pd.DataFrame()
    chart1 = save_absenteeism_chart(
        empty_df, tmp_path / "empty_abs.png", "Empty Absenteeism"
    )
    chart2 = save_monthly_attendance_chart(
        empty_df, tmp_path / "empty_month.png", "Empty Monthly"
    )

    for path in (chart1, chart2):
        assert path.exists()
        assert path.stat().st_size > 0
        with open(path, "rb") as f:
            assert f.read(4) == b"\x89PNG"


def test_db_generate_monthly_report(conn):
    """Database tests for generate_monthly_report."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Absent")
    record_attendance(conn, "E002", datetime.date(2026, 9, 1), "Present")

    report = generate_monthly_report(conn, 2026, 9)
    assert "50.00%" in report  # E001 attendance
    assert "100.00%" in report  # E002 attendance
    assert "Total present: 2" in report
    assert "Total absent: 1" in report
    assert "Total eligible days: 3" in report
    assert "Overall attendance: 66.67%" in report

    # Month with no attendance records
    no_records = generate_monthly_report(conn, 2026, 8)
    assert no_records == "No attendance records for 2026-08."

    # Invalid month numbers
    with pytest.raises(ValueError):
        generate_monthly_report(conn, 2026, 13)
    with pytest.raises(ValueError):
        generate_monthly_report(conn, 2026, 0)


def test_db_year_end_monthly_report(conn):
    """Year end report for 2026-12."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 12, 31), "Present")

    report = generate_monthly_report(conn, 2026, 12)
    assert "Total present: 1" in report
    assert "Overall attendance: 100.00%" in report


def test_db_reconciliation(conn):
    """Reconciliation test (AC-03): totals in report match manual count from get_attendance."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Absent")
    record_attendance(conn, "E001", datetime.date(2026, 9, 3), "Leave")
    record_attendance(conn, "E001", datetime.date(2026, 9, 4), "Present")
    record_holiday(conn, datetime.date(2026, 9, 14))

    att_rows = get_attendance(
        conn,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 30),
    )
    present_count = sum(1 for r in att_rows if r["status"] == "Present")
    absent_count = sum(1 for r in att_rows if r["status"] == "Absent")
    leave_count = sum(1 for r in att_rows if r["status"] == "Leave")
    holiday_count = sum(1 for r in att_rows if r["status"] == "Holiday")
    eligible_count = present_count + absent_count + leave_count

    report = generate_monthly_report(conn, 2026, 9)
    assert f"Total present: {present_count}" in report
    assert f"Total absent: {absent_count}" in report
    assert f"Total leave: {leave_count}" in report
    assert f"Total holiday: {holiday_count}" in report
    assert f"Total eligible days: {eligible_count}" in report


def test_db_export_charts(conn, tmp_path):
    """export_charts returns 2 paths and both files exist."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")

    paths = export_charts(conn, 2026, 9, output_dir=str(tmp_path))
    assert len(paths) == 2
    for p in paths:
        assert isinstance(p, Path)
        assert p.exists()
        assert p.stat().st_size > 0
        with open(p, "rb") as f:
            assert f.read(4) == b"\x89PNG"
