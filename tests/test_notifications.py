"""Tests for Module 6 / Phase 7: In-Website Notification System & Review Status.

Verifies:
- In-app notification badge counts and summary metrics.
- Alert email formatting with HTML and plain text compliance warnings.
- SMTP dispatch mechanism with graceful simulated fallback when SMTP is unconfigured.
- Notification bell and active unreviewed counter rendering in web UI.
"""

from typing import Any
import pytest
import config
from src.attendance import record_attendance
from src.employees import add_employee
from src.alerts import sync_monthly_attendance_alerts
from src.notifications import (
    dispatch_warning_notification,
    format_alert_email_content,
    get_notification_summary,
)
from src.web import create_app


def test_format_alert_email_content() -> None:
    """Verify HTML and plain text email generation for attendance alerts."""
    subject, html = format_alert_email_content(
        employee_name="Marie Curie",
        employee_code="E950",
        period_label="September 2026",
        attendance_pct=60.0,
        threshold=75.0,
        present_days=3,
        absent_days=2,
        eligible_days=5,
    )

    assert "Marie Curie" in subject
    assert "E950" in subject
    assert "September 2026" in subject
    assert "60.0%" in html
    assert "75.0%" in html
    assert "AttendIQ Compliance Alert" in html


def test_dispatch_warning_notification_simulated() -> None:
    """Verify graceful fallback to simulated dispatch when SMTP environment is unset."""
    res = dispatch_warning_notification(
        recipient_email="supervisor@company.com",
        employee_name="Alan Turing",
        employee_code="E951",
        period_label="September 2026",
        attendance_pct=50.0,
        threshold=75.0,
        present_days=2,
        absent_days=2,
        eligible_days=4,
    )

    assert res["status"] == "simulated"
    assert res["delivered"] is False
    assert res["recipient"] == "supervisor@company.com"
    assert "Alan Turing" in res["subject"]


def test_notification_summary_and_web_bell(conn: Any) -> None:
    """Verify in-app notification overview and top-bar bell badge rendering."""
    emp_id = add_employee(conn, "E952", "Notification Test Subject", "Quality", "2026-09-01")

    # Record attendance: 1 present, 3 absent -> 25% (Critical warning)
    record_attendance(conn, "E952", "2026-09-01", "Present")
    record_attendance(conn, "E952", "2026-09-02", "Absent")
    record_attendance(conn, "E952", "2026-09-03", "Absent")
    record_attendance(conn, "E952", "2026-09-04", "Absent")

    # Sync alerts
    sync_monthly_attendance_alerts(conn, 2026, 9)

    # 1. Test notification summary function
    summary = get_notification_summary(conn)
    assert summary["unreviewed_count"] >= 1
    assert summary["critical_unreviewed"] >= 1

    # 2. Test top-bar bell in web app
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-notifications",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "Admin"

    res = client.get("/employees")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Bell icon and unreviewed warning counter
    assert "top-bar-bell-btn" in html
    assert "/alerts?reviewed=false" in html

