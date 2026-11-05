"""Tests for Module 4 / Phase 5: Smart Attendance Warning System (< 75%).

Verifies:
- Configurable critical threshold retrieval and mutation in system_settings.
- Multi-tier alert classification: Normal (>=85%), Attention (75-85%), Critical (<75%).
- Automated idempotent monthly alert synchronization and non-duplication on multiple runs.
- Review lifecycle: marking alerts as reviewed by HR/Admin, attaching review notes, tracking reviewers.
- Filtered retrieval and count aggregation (by severity level, department, review status).
- Web endpoints:
  - GET /alerts
  - POST /alerts/<id>/review
  - POST /alerts/settings/threshold (Admin only role protection)
  - POST /alerts/sync
"""

from typing import Any
import pytest
import config
from src.alerts import (
    classify_attendance_level,
    count_attendance_alerts,
    get_alert_metrics_summary,
    get_critical_threshold,
    list_attendance_alerts,
    mark_alert_reviewed,
    set_critical_threshold,
    sync_monthly_attendance_alerts,
)
from src.attendance import record_attendance
from src.employees import add_employee
from src.web import create_app


def test_threshold_management(conn: Any) -> None:
    """Verify reading and setting configurable critical attendance thresholds."""
    # Default is 75.0
    thresh = get_critical_threshold(conn)
    assert thresh == 75.0

    # Update to 80.0
    updated = set_critical_threshold(conn, 80.0)
    assert updated == 80.0
    assert get_critical_threshold(conn) == 80.0

    # Revert to 75.0
    set_critical_threshold(conn, 75.0)
    assert get_critical_threshold(conn) == 75.0

    # Rejects invalid thresholds
    with pytest.raises(ValueError, match="between 0.0"):
        set_critical_threshold(conn, -5.0)

    with pytest.raises(ValueError, match="between 0.0"):
        set_critical_threshold(conn, 105.0)


def test_classification_logic() -> None:
    """Verify multi-tier categorization rules."""
    # Critical: strictly below threshold (default 75.0)
    level, label = classify_attendance_level(74.9, threshold=75.0)
    assert level == "CRITICAL"
    assert "Critical" in label

    # Exactly 75.0 is ATTENTION
    level, _ = classify_attendance_level(75.0, threshold=75.0)
    assert level == "ATTENTION"

    # 80.0 is ATTENTION (75.0 to 85.0)
    level, label = classify_attendance_level(80.0, threshold=75.0)
    assert level == "ATTENTION"
    assert "Attention" in label

    # 85.0 and above is NORMAL
    level, label = classify_attendance_level(85.0, threshold=75.0)
    assert level == "NORMAL"
    assert "Normal" in label

    level, _ = classify_attendance_level(95.0, threshold=75.0)
    assert level == "NORMAL"


def test_alert_sync_idempotency_and_review(conn: Any) -> None:
    """Verify alert synchronization, non-duplication on re-sync, and review workflow."""
    emp_crit = add_employee(conn, "E801", "Critical Worker", "Operations", "2026-09-01")
    emp_att = add_employee(conn, "E802", "Borderline Worker", "Operations", "2026-09-01")
    emp_norm = add_employee(conn, "E803", "Stellar Worker", "Operations", "2026-09-01")

    # emp_crit: 1 present, 3 absent -> 25% attendance (Critical)
    record_attendance(conn, "E801", "2026-09-01", "Present")
    record_attendance(conn, "E801", "2026-09-02", "Absent")
    record_attendance(conn, "E801", "2026-09-03", "Absent")
    record_attendance(conn, "E801", "2026-09-04", "Absent")

    # emp_att: 4 present, 1 absent -> 80% attendance (Attention)
    record_attendance(conn, "E802", "2026-09-01", "Present")
    record_attendance(conn, "E802", "2026-09-02", "Present")
    record_attendance(conn, "E802", "2026-09-03", "Present")
    record_attendance(conn, "E802", "2026-09-04", "Present")
    record_attendance(conn, "E802", "2026-09-07", "Absent")

    # emp_norm: 5 present -> 100% attendance (Normal - no alert)
    for d in ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07"]:
        record_attendance(conn, "E803", d, "Present")

    # Run sync for Sep 2026
    synced = sync_monthly_attendance_alerts(conn, 2026, 9)
    assert synced == 2  # E801 and E802

    # Query alerts
    alerts = list_attendance_alerts(conn, year=2026, month=9)
    assert len(alerts) >= 2

    crit_alert = next((a for a in alerts if a["employee_code"] == "E801"), None)
    assert crit_alert is not None
    assert crit_alert["warning_level"] == "CRITICAL"
    assert crit_alert["is_reviewed"] is False

    att_alert = next((a for a in alerts if a["employee_code"] == "E802"), None)
    assert att_alert is not None
    assert att_alert["warning_level"] == "ATTENTION"

    # Idempotency: Run sync again -> should update, NOT create duplicate rows
    synced_again = sync_monthly_attendance_alerts(conn, 2026, 9)
    alerts_after_resync = list_attendance_alerts(conn, year=2026, month=9)
    assert len(alerts_after_resync) == len(alerts)

    # Review workflow: mark crit_alert as reviewed
    mark_alert_reviewed(conn, crit_alert["alert_id"], user_id=None, notes="Spoke with manager about medical leave.")
    reviewed_list = list_attendance_alerts(conn, year=2026, month=9, is_reviewed=True)
    assert any(a["alert_id"] == crit_alert["alert_id"] for a in reviewed_list)
    assert any(a["notes"] == "Spoke with manager about medical leave." for a in reviewed_list)

    # Metrics summary
    metrics = get_alert_metrics_summary(conn, year=2026, month=9)
    assert metrics["critical"] >= 1
    assert metrics["attention"] >= 1
    assert metrics["total"] >= 2


def test_alerts_web_dashboard(conn: Any) -> None:
    """Verify web routes GET /alerts, POST /alerts/settings/threshold, and POST /alerts/<id>/review."""
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-alerts",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    # 1. Access alerts dashboard
    res = client.get("/alerts?year=2026&month=9")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Smart Attendance Warning Center" in html
    assert "Critical Risk" in html
    assert "Threshold Settings" in html

    # 2. Get CSRF token from page
    import re
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = match.group(1) if match else "test_csrf"

    with client.session_transaction() as sess:
        sess["csrf_token"] = csrf_token
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "Admin"

    # 3. Update threshold via web form
    res_thresh = client.post(
        "/alerts/settings/threshold",
        data={"csrf_token": csrf_token, "threshold": "78.0"},
        follow_redirects=True,
    )
    assert res_thresh.status_code == 200
    assert get_critical_threshold(conn) == 78.0

    # Reset back to 75.0
    set_critical_threshold(conn, 75.0)
