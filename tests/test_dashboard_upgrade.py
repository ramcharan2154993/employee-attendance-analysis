"""Tests for Module 7 / Phase 8: Executive Admin Dashboard Upgrade.

Verifies:
- Executive KPI summary cards: Active headcount, Org attendance rate, Critical Risk (< 75%), Attention.
- Dedicated Attendance Warning Center widget on dashboard.
- Department Attendance Health breakdown table.
- 1-click Quick Export shortcuts for PDF and Excel statements.
"""

from typing import Any
import pytest
import config
from src.attendance import record_attendance
from src.employees import add_employee
from src.alerts import sync_monthly_attendance_alerts
from src.web import create_app


def test_executive_dashboard_rendering(conn: Any) -> None:
    """Verify that the dashboard displays executive alert KPIs, warning widgets, and department tables."""
    emp1 = add_employee(conn, "E981", "Executive Lead", "Management", "2026-09-01")
    emp2 = add_employee(conn, "E982", "Low Attendant", "Sales", "2026-09-01")

    # Management: High attendance (100%)
    record_attendance(conn, "E981", "2026-09-01", "Present")
    record_attendance(conn, "E981", "2026-09-02", "Present")

    # Sales: 1 present, 3 absent -> 25% (Critical risk < 75%)
    record_attendance(conn, "E982", "2026-09-01", "Present")
    record_attendance(conn, "E982", "2026-09-02", "Absent")
    record_attendance(conn, "E982", "2026-09-03", "Absent")
    record_attendance(conn, "E982", "2026-09-04", "Absent")

    # Sync alerts for Sep 2026
    sync_monthly_attendance_alerts(conn, 2026, 9)

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-dashboard",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "Admin"

    res = client.get("/?year=2026&month=9")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # 1. Executive KPI Cards
    assert "CRITICAL RISK" in html
    assert "ATTENTION NEEDED" in html
    assert "ORG ATTENDANCE" in html

    # 2. Quick Export Shortcuts
    assert "PDF Report" in html
    assert "Excel Export" in html
    assert "/reports/department/pdf" in html
    assert "/reports/department/excel" in html

    # 3. Attendance Warning Center Widget
    assert "Attendance Warning Center" in html
    assert "Low Attendant" in html
    assert "E982" in html
    assert "CRITICAL" in html

    # 4. Department Attendance Health Breakdown Table
    assert "Department Attendance Health" in html
    assert "Management" in html
    assert "Sales" in html

