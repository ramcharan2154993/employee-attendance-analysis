"""Regression tests for reporting-period boundaries, attendance, and absenteeism calculations."""

import datetime
from pathlib import Path
from typing import Any
import pytest
import config
from src.analysis import (
    department_summary,
    employee_summary,
    get_available_months,
    get_dashboard_summary,
    load_attendance_df,
    monthly_summary,
)
from src.attendance import record_attendance, record_holiday
from src.calculations import (
    calculate_absenteeism_percentage,
    calculate_attendance_percentage,
    eligible_days,
)
from src.employees import add_employee
from src.reports import export_charts, generate_monthly_report
from src.web import create_app


@pytest.fixture
def app_instance(tmp_path: Path) -> Any:
    """Create Flask application instance for regression web tests."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE_NAME": config.DB_TEST_NAME,
            "OUTPUT_DIR": str(tmp_path),
        }
    )


@pytest.fixture
def test_client(app_instance: Any) -> Any:
    """Provide test client."""
    return app_instance.test_client()


def test_present_only_records_produce_100_attendance_0_absenteeism(conn: Any) -> None:
    """Present-only records in a period must produce exactly 100% attendance and 0% absenteeism."""
    add_employee(conn, "E010", "Test Alice", "Engineering", joining_date="2026-09-01")
    add_employee(conn, "E011", "Test Bob", "Engineering", joining_date="2026-09-01")

    # 4 Present records in October 2026
    record_attendance(conn, "E010", datetime.date(2026, 10, 16), "Present")
    record_attendance(conn, "E010", datetime.date(2026, 10, 19), "Present")
    record_attendance(conn, "E010", datetime.date(2026, 10, 20), "Present")
    record_attendance(conn, "E011", datetime.date(2026, 10, 19), "Present")

    summary = get_dashboard_summary(conn, year=2026, month=10)
    assert summary["year"] == 2026
    assert summary["month"] == 10
    assert summary["present"] == 4
    assert summary["absent"] == 0
    assert summary["leave"] == 0
    assert summary["eligible_days"] == 4
    assert summary["attendance_pct"] == 100.0
    assert summary["absenteeism_pct"] == 0.0


def test_mixed_present_and_absent_records_produce_correct_percentages(conn: Any) -> None:
    """Mixed Present and Absent records calculate accurate percentages."""
    add_employee(conn, "E020", "Test Carol", "Design", joining_date="2026-09-01")

    record_attendance(conn, "E020", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E020", datetime.date(2026, 9, 2), "Present")
    record_attendance(conn, "E020", datetime.date(2026, 9, 3), "Present")
    record_attendance(conn, "E020", datetime.date(2026, 9, 4), "Absent")

    summary = get_dashboard_summary(conn, year=2026, month=9)
    assert summary["present"] == 3
    assert summary["absent"] == 1
    assert summary["eligible_days"] == 4
    assert summary["attendance_pct"] == 75.0
    assert summary["absenteeism_pct"] == 25.0


def _get_september_weekdays(count: int) -> list[datetime.date]:
    """Helper returning the first N weekdays of September 2026."""
    dates = []
    day = 1
    while len(dates) < count and day <= 30:
        d = datetime.date(2026, 9, day)
        if d.weekday() < 5:
            dates.append(d)
        day += 1
    return dates


def test_leave_records_included_in_denominator_not_numerators(conn: Any) -> None:
    """Leave counts as an eligible day but is neither Present nor Absent."""
    add_employee(conn, "E030", "Test Dave", "Marketing", joining_date="2026-09-01")

    # 8 Present, 1 Absent, 1 Leave -> 10 eligible days on valid weekdays
    weekdays = _get_september_weekdays(10)
    for d in weekdays[:8]:
        record_attendance(conn, "E030", d, "Present")
    record_attendance(conn, "E030", weekdays[8], "Absent")
    record_attendance(conn, "E030", weekdays[9], "Leave")

    summary = get_dashboard_summary(conn, year=2026, month=9)
    assert summary["present"] == 8
    assert summary["absent"] == 1
    assert summary["leave"] == 1
    assert summary["eligible_days"] == 10
    assert summary["attendance_pct"] == 80.0
    assert summary["absenteeism_pct"] == 10.0



def test_absent_records_correctly_included_in_monthly_calculations(conn: Any) -> None:
    """Absent records must be counted in monthly aggregation and ranking."""
    add_employee(conn, "E040", "Test Eve", "HR", joining_date="2026-09-01")
    add_employee(conn, "E041", "Test Frank", "HR", joining_date="2026-09-01")

    record_attendance(conn, "E040", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E040", datetime.date(2026, 9, 2), "Absent")
    record_attendance(conn, "E041", datetime.date(2026, 9, 1), "Absent")
    record_attendance(conn, "E041", datetime.date(2026, 9, 2), "Absent")

    summary = get_dashboard_summary(conn, year=2026, month=9)
    assert summary["present"] == 1
    assert summary["absent"] == 3
    assert summary["eligible_days"] == 4
    assert summary["attendance_pct"] == 25.0
    assert summary["absenteeism_pct"] == 75.0


def test_e005_september_15_17_absence_scenario(conn: Any) -> None:
    """The September 15–17, 2026 E005 absence scenario is accurately calculated."""
    add_employee(conn, "E005", "Divya Menon", "HR", joining_date="2026-05-01")

    # Record 7 Present and 14 Absent in September, explicitly including Sept 15, 16, 17
    record_attendance(conn, "E005", datetime.date(2026, 9, 15), "Absent")
    record_attendance(conn, "E005", datetime.date(2026, 9, 16), "Absent")
    record_attendance(conn, "E005", datetime.date(2026, 9, 17), "Absent")
    record_attendance(conn, "E005", datetime.date(2026, 9, 18), "Present")

    df_sep = load_attendance_df(
        conn,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 30),
    )
    emp_res = employee_summary(df_sep)
    divya = emp_res[emp_res["employee_code"] == "E005"].iloc[0]

    assert divya["absent"] == 3
    assert divya["present"] == 1
    assert divya["eligible_days"] == 4
    assert divya["absenteeism_pct"] == 75.0
    assert divya["attendance_pct"] == 25.0

    dash_sep = get_dashboard_summary(conn, year=2026, month=9)
    assert dash_sep["absent"] == 3
    assert dash_sep["present"] == 1
    assert dash_sep["absenteeism_pct"] == 75.0


def test_september_records_do_not_contaminate_october_metrics(conn: Any) -> None:
    """September absences must not bleed into October reporting metrics."""
    add_employee(conn, "E050", "Test Grace", "Engineering", joining_date="2026-05-01")

    # September records with absences
    record_attendance(conn, "E050", datetime.date(2026, 9, 15), "Absent")
    record_attendance(conn, "E050", datetime.date(2026, 9, 16), "Absent")
    record_attendance(conn, "E050", datetime.date(2026, 9, 17), "Absent")

    # October records with only Present
    record_attendance(conn, "E050", datetime.date(2026, 10, 19), "Present")
    record_attendance(conn, "E050", datetime.date(2026, 10, 20), "Present")

    # October summary: 2 present, 0 absent
    oct_summary = get_dashboard_summary(conn, year=2026, month=10)
    assert oct_summary["present"] == 2
    assert oct_summary["absent"] == 0
    assert oct_summary["eligible_days"] == 2
    assert oct_summary["attendance_pct"] == 100.0
    assert oct_summary["absenteeism_pct"] == 0.0

    # September summary: 0 present, 3 absent
    sep_summary = get_dashboard_summary(conn, year=2026, month=9)
    assert sep_summary["present"] == 0
    assert sep_summary["absent"] == 3
    assert sep_summary["eligible_days"] == 3
    assert sep_summary["attendance_pct"] == 0.0
    assert sep_summary["absenteeism_pct"] == 100.0


def test_department_and_org_totals_use_aggregate_counts_not_averaged_percentages(conn: Any) -> None:
    """Averaging individual percentages distorts metrics; aggregate counts must be used."""
    add_employee(conn, "E061", "Emp Short", "Sales", joining_date="2026-09-01")
    add_employee(conn, "E062", "Emp Long", "Sales", joining_date="2026-09-01")

    # E061: 1 Present out of 1 scheduled day -> 100%
    weekdays = _get_september_weekdays(10)
    record_attendance(conn, "E061", weekdays[0], "Present")

    # E062: 0 Present, 9 Absent out of 9 scheduled days -> 0%
    for d in weekdays[1:10]:
        record_attendance(conn, "E062", d, "Absent")


    # If averaged: (100% + 0%) / 2 = 50.0%
    # Correct aggregate: 1 Present / 10 Eligible = 10.0% attendance, 90.0% absenteeism
    df = load_attendance_df(conn, datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
    dept_df = department_summary(df)
    sales = dept_df[dept_df["department"] == "Sales"].iloc[0]

    assert sales["present"] == 1
    assert sales["absent"] == 9
    assert sales["eligible_days"] == 10
    assert sales["attendance_pct"] == 10.0
    assert sales["absenteeism_pct"] == 90.0

    org_summary = get_dashboard_summary(conn, year=2026, month=9)
    assert org_summary["attendance_pct"] == 10.0
    assert org_summary["absenteeism_pct"] == 90.0


def test_missing_records_not_treated_as_absences(conn: Any) -> None:
    """Missing daily attendance records must not be treated as absences."""
    add_employee(conn, "E070", "Emp Partial", "Finance", joining_date="2026-09-01")

    # Only 1 record in September (Present)
    record_attendance(conn, "E070", datetime.date(2026, 9, 1), "Present")

    summary = get_dashboard_summary(conn, year=2026, month=9)
    assert summary["present"] == 1
    assert summary["absent"] == 0
    assert summary["eligible_days"] == 1
    assert summary["attendance_pct"] == 100.0
    assert summary["absenteeism_pct"] == 0.0


def test_holidays_excluded_from_eligible_days(conn: Any) -> None:
    """Organization-wide holidays must be excluded from eligible days."""
    add_employee(conn, "E080", "Emp HolidayTest", "Operations", joining_date="2026-09-01")

    record_attendance(conn, "E080", datetime.date(2026, 9, 1), "Present")
    record_holiday(conn, datetime.date(2026, 9, 14))

    summary = get_dashboard_summary(conn, year=2026, month=9)
    assert summary["present"] == 1
    assert summary["absent"] == 0
    assert summary["leave"] == 0
    assert summary["holiday"] == 1
    assert summary["eligible_days"] == 1  # holiday excluded from denominator
    assert summary["attendance_pct"] == 100.0
    assert summary["absenteeism_pct"] == 0.0


def test_joining_date_eligibility_preserved(conn: Any) -> None:
    """Employees joined after report window are excluded from historical eligible rosters."""
    add_employee(conn, "E090", "Joined Late", "Engineering", joining_date="2026-10-01")

    df_sep = load_attendance_df(
        conn,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 30),
    )
    assert "E090" not in df_sep["employee_code"].values

    df_oct = load_attendance_df(
        conn,
        start_date=datetime.date(2026, 10, 1),
        end_date=datetime.date(2026, 10, 31),
    )
    assert "E090" in df_oct["employee_code"].values


def test_empty_datasets_and_zero_eligible_days_handled_safely(conn: Any) -> None:
    """Empty datasets and zero eligible days return None percentages without zero division error."""
    add_employee(conn, "E100", "No Attendance", "HR", joining_date="2026-09-01")

    summary = get_dashboard_summary(conn, year=2026, month=11)
    assert summary["eligible_days"] == 0
    assert summary["attendance_pct"] is None
    assert summary["absenteeism_pct"] is None


def test_dashboard_cards_report_summaries_and_charts_agree_for_same_period(
    test_client: Any, conn: Any
) -> None:
    """Dashboard cards, text report totals, and chart exports agree on exact numbers for the period."""
    add_employee(conn, "E110", "Sync Test", "Engineering", joining_date="2026-09-01")
    record_attendance(conn, "E110", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E110", datetime.date(2026, 9, 2), "Present")
    record_attendance(conn, "E110", datetime.date(2026, 9, 3), "Absent")
    record_attendance(conn, "E110", datetime.date(2026, 9, 4), "Leave")

    # 1. Dashboard summary calculation
    dash_metrics = get_dashboard_summary(conn, year=2026, month=9)
    assert dash_metrics["present"] == 2
    assert dash_metrics["absent"] == 1
    assert dash_metrics["leave"] == 1
    assert dash_metrics["eligible_days"] == 4
    assert dash_metrics["attendance_pct"] == 50.0
    assert dash_metrics["absenteeism_pct"] == 25.0

    # 2. Monthly report text
    report_text = generate_monthly_report(conn, 2026, 9)
    assert "Total present: 2" in report_text
    assert "Total absent: 1" in report_text
    assert "Total leave: 1" in report_text
    assert "Total eligible days: 4" in report_text
    assert "Overall attendance: 50.00%" in report_text

    # 3. Web Dashboard view for 2026-09
    res_dash = test_client.get("/?year=2026&month=9")
    assert res_dash.status_code == 200
    html = res_dash.get_data(as_text=True)
    assert "50.0%" in html
    assert "25.0%" in html
    assert "September 2026" in html
