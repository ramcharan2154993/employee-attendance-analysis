"""Tests for Module 5 / Phase 6: Advanced Employee Attendance Diagnostics & Heatmaps.

Verifies:
- Monthly calendar matrix generation with day-by-day attendance status mapping.
- Consecutive absence streak detection, tracking max streaks and start/end dates.
- Day-of-week absence distribution (Monday through Friday breakdown).
- Multi-month attendance trend text and factual diagnostic summaries.
- Web rendering of the diagnostic cards, streak metrics, warning banners, and calendar heatmap.
"""

from typing import Any
import pytest
import config
from src.analysis import (
    analyze_employee_patterns,
    build_employee_calendar_matrix,
)
from src.attendance import record_attendance
from src.employees import add_employee
from src.web import create_app


def test_build_employee_calendar_matrix() -> None:
    """Verify that build_employee_calendar_matrix constructs accurate 7-column calendar grids."""
    records = [
        {"attendance_date": "2026-09-01", "status": "Present", "attendance_id": 101},
        {"attendance_date": "2026-09-02", "status": "Absent", "attendance_id": 102},
        {"attendance_date": "2026-09-03", "status": "Leave", "attendance_id": 103},
        {"attendance_date": "2026-09-04", "status": "Present", "attendance_id": 104},
        {"attendance_date": "2026-09-07", "status": "Holiday", "attendance_id": 105},
    ]

    cal = build_employee_calendar_matrix(2026, 9, records)

    assert cal["year"] == 2026
    assert cal["month"] == 9
    assert "September 2026" in cal["month_label"]

    weeks = cal["weeks"]
    assert len(weeks) >= 4

    # Every week must have exactly 7 days (Mon-Sun)
    for w in weeks:
        assert len(w) == 7

    # Sept 1, 2026 was a Tuesday -> Monday (index 0) in week 1 must be padding
    first_week = weeks[0]
    assert first_week[0]["is_padding"] is True
    assert first_week[1]["day"] == 1
    assert first_week[1]["status"] == "Present"
    assert first_week[1]["attendance_id"] == 101

    # Sept 5 and Sept 6 are Saturday and Sunday (weekends)
    assert first_week[5]["is_weekend"] is True
    assert first_week[5]["status"] == "Weekend"
    assert first_week[6]["is_weekend"] is True
    assert first_week[6]["status"] == "Weekend"

    # Status counts verification
    counts = cal["status_counts"]
    assert counts["Present"] == 2
    assert counts["Absent"] == 1
    assert counts["Leave"] == 1
    assert counts["Holiday"] == 1


def test_analyze_employee_patterns_streaks_and_weekdays() -> None:
    """Verify streak detection and weekday aggregation across dates."""
    # 3 consecutive absences: Sep 1 (Tue), Sep 2 (Wed), Sep 3 (Thu)
    records = [
        {"attendance_date": "2026-09-01", "status": "Absent"},
        {"attendance_date": "2026-09-02", "status": "Absent"},
        {"attendance_date": "2026-09-03", "status": "Absent"},
        {"attendance_date": "2026-09-04", "status": "Present"},
        {"attendance_date": "2026-09-07", "status": "Absent"},  # Monday
        {"attendance_date": "2026-09-08", "status": "Present"},
    ]

    monthly_trends = [
        {"period": "2026-08", "label": "Aug 2026", "attendance_pct": 90.0},
        {"period": "2026-09", "label": "Sep 2026", "attendance_pct": 50.0},
    ]

    patterns = analyze_employee_patterns(records, monthly_trends, critical_threshold=75.0)

    assert patterns["max_consecutive_absences"] == 3
    assert str(patterns["max_streak_start"]) == "2026-09-01"
    assert str(patterns["max_streak_end"]) == "2026-09-03"

    # Weekday absences
    w_abs = patterns["weekday_absences"]
    assert w_abs["Monday"] == 1
    assert w_abs["Tuesday"] == 1
    assert w_abs["Wednesday"] == 1
    assert w_abs["Thursday"] == 1
    assert w_abs["Friday"] == 0

    assert patterns["months_below_threshold"] == 1
    assert "declined" in patterns["trend_description"].lower()
    assert "maximum consecutive absence streak was 3 day(s)" in patterns["factual_summary"]


def test_employee_profile_diagnostics_web(conn: Any) -> None:
    """Verify web view renders diagnostics, calendar matrix, and compliance badges."""
    emp_id = add_employee(conn, "E901", "Diagnostics Test Subject", "Engineering", "2026-09-01")

    # Record attendance in Sep 2026: 1 present, 3 absent -> 25% attendance (Critical warning)
    record_attendance(conn, "E901", "2026-09-01", "Present")
    record_attendance(conn, "E901", "2026-09-02", "Absent")
    record_attendance(conn, "E901", "2026-09-03", "Absent")
    record_attendance(conn, "E901", "2026-09-04", "Absent")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-diagnostics",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    res = client.get(f"/employees/{emp_id}?year=2026&month=9")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Warning banner
    assert "CRITICAL ATTENDANCE RISK" in html
    assert "Below 75% Threshold" in html

    # 2. Behavioral diagnostics
    assert "Behavioral Patterns &amp; Attendance Diagnostics" in html or "Behavioral Patterns & Attendance Diagnostics" in html
    assert "Consecutive Absence Streak" in html
    assert "working days" in html
    assert "Most Frequent Absence Day" in html

    # 3. Calendar heatmap
    assert "Attendance Calendar" in html
    assert "September 2026" in html
    assert "Mon" in html and "Fri" in html
