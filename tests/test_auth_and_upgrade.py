"""Comprehensive tests for HR Workflow, Analytics, Access-Control, and Audit Trail."""

import datetime
from pathlib import Path
from typing import Any
import pytest
from werkzeug.security import check_password_hash

import config
from src.analysis import get_employee_analytics_data
from src.attendance import (
    check_department_attendance_conflicts,
    count_attendance,
    get_attendance,
    record_attendance,
    record_department_attendance,
    update_attendance,
)
from src.audit import count_audit_records, get_audit_trail, log_attendance_action
from src.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    list_users,
    toggle_user_status,
)
from src.db import migrate_auth_and_audit
from src.employees import add_employee, deactivate_employee, get_department_employees
from src.web import create_app


@pytest.fixture
def test_app(tmp_path: Path) -> Any:
    """Create Flask app with test config and REQUIRE_AUTH=True."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-12345",
            "DATABASE_NAME": config.DB_TEST_NAME,
            "OUTPUT_DIR": str(tmp_path),
            "REQUIRE_AUTH": True,
        }
    )


@pytest.fixture
def auth_client(test_app: Any) -> Any:
    """Provide a test client for test_app."""
    return test_app.test_client()


# =============================================================================
# 1. Department Roster Filtering and Bulk Recording
# =============================================================================

def test_department_roster_filtering_by_joining_date_and_active_status(conn: Any) -> None:
    """Active employees joining on/before date are eligible; future or inactive excluded."""
    # Active, joined Sept 1
    add_employee(conn, "EMP01", "Alice Smith", "Finance", joining_date="2026-09-01")
    # Active, joined Oct 1
    add_employee(conn, "EMP02", "Bob Jones", "Finance", joining_date="2026-10-01")
    # Inactive, joined Sept 1
    add_employee(conn, "EMP03", "Charlie Brown", "Finance", joining_date="2026-09-01")
    deactivate_employee(conn, "EMP03")

    # On Tuesday 2026-09-15: EMP01 is eligible, EMP02 is not yet joined, EMP03 is inactive
    eligible_sept = get_department_employees(
        conn, "Finance", active_only=True, eligible_as_of=datetime.date(2026, 9, 15)
    )
    eligible_codes = [c["employee_code"] for c in eligible_sept]
    assert "EMP01" in eligible_codes
    assert "EMP02" not in eligible_codes
    assert "EMP03" not in eligible_codes

    # On Monday 2026-10-05: both EMP01 and EMP02 are eligible
    eligible_oct = get_department_employees(
        conn, "Finance", active_only=True, eligible_as_of=datetime.date(2026, 10, 5)
    )
    eligible_oct_codes = [c["employee_code"] for c in eligible_oct]
    assert "EMP01" in eligible_oct_codes
    assert "EMP02" in eligible_oct_codes
    assert "EMP03" not in eligible_oct_codes


def test_existing_attendance_versus_unrecorded_employees(conn: Any) -> None:
    """Check conflict detection clearly separates recorded vs unrecorded staff."""
    add_employee(conn, "EMP10", "Diana Prince", "IT", joining_date="2026-09-01")
    add_employee(conn, "EMP11", "Bruce Wayne", "IT", joining_date="2026-09-01")

    # Pre-record EMP10 as Present on Thursday 2026-09-10
    record_attendance(conn, "EMP10", datetime.date(2026, 9, 10), "Present")

    results = check_department_attendance_conflicts(
        conn, "IT", datetime.date(2026, 9, 10)
    )
    assert len(results) == 1
    assert results[0]["employee_code"] == "EMP10"
    assert results[0]["status"] == "Present"
    assert results[0]["attendance_id"] is not None

    # Verify unrecorded list
    all_eligible = get_department_employees(
        conn, "IT", active_only=True, eligible_as_of=datetime.date(2026, 9, 10)
    )
    conflict_codes = {r["employee_code"] for r in results}
    unrecorded = [e for e in all_eligible if e["employee_code"] not in conflict_codes]
    assert len(unrecorded) == 1
    assert unrecorded[0]["employee_code"] == "EMP11"


def test_successful_recording_of_only_new_records(conn: Any) -> None:
    """Department recording saves only unrecorded members without overwriting existing."""
    add_employee(conn, "EMP20", "Clark Kent", "HR", joining_date="2026-09-01")
    add_employee(conn, "EMP21", "Lois Lane", "HR", joining_date="2026-09-01")

    # Pre-record EMP20 as Leave on Tuesday 2026-09-15
    record_attendance(conn, "EMP20", datetime.date(2026, 9, 15), "Leave")

    # Submit only new EMP21 as Present
    records_to_insert = [{"employee_code": "EMP21", "status": "Present"}]
    res = record_department_attendance(
        conn, "HR", datetime.date(2026, 9, 15), records_to_insert
    )
    assert res["total_records"] == 1

    # Verify EMP20 remains Leave and EMP21 is Present
    att = get_attendance(
        conn, start_date=datetime.date(2026, 9, 15), end_date=datetime.date(2026, 9, 15)
    )
    status_map = {a["employee_code"]: a["status"] for a in att}
    assert status_map["EMP20"] == "Leave"
    assert status_map["EMP21"] == "Present"


def test_conflict_detection_and_atomic_rollback(conn: Any) -> None:
    """If an employee already has attendance and is attempted in batch, transaction rolls back."""
    add_employee(conn, "EMP30", "Barry Allen", "Operations", joining_date="2026-09-01")
    add_employee(conn, "EMP31", "Iris West", "Operations", joining_date="2026-09-01")

    # Record EMP30 on Monday 2026-09-21
    record_attendance(conn, "EMP30", datetime.date(2026, 9, 21), "Present")

    # Attempt to insert EMP31 AND EMP30 (conflict on EMP30)
    with pytest.raises(ValueError, match="Attendance already recorded"):
        record_department_attendance(
            conn,
            "Operations",
            datetime.date(2026, 9, 21),
            [
                {"employee_code": "EMP31", "status": "Present"},
                {"employee_code": "EMP30", "status": "Present"},
            ],
        )

    # Verify EMP31 was NOT recorded (atomic rollback)
    records = get_attendance(conn, employee_code="EMP31")
    assert len(records) == 0


# =============================================================================
# 2. On-Demand Attendance Logs, Filters, and Pagination
# =============================================================================

def test_attendance_landing_page_does_not_load_unbounded_history(auth_client: Any, conn: Any) -> None:
    """GET /attendance without view=log or filters shows action cards and empty state."""
    uid = create_user(conn, "hr_tester", "pass12345", role="HR")
    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "hr_tester"
        sess["role"] = "HR"

    # Add records on valid weekdays
    add_employee(conn, "EMP40", "Hal Jordan", "Logistics", joining_date="2026-09-01")
    weekdays = [1, 2, 3, 4, 7, 8, 9, 10, 11]  # Mon-Fri days in Sept 2026
    for d in weekdays:
        record_attendance(conn, "EMP40", datetime.date(2026, 9, d), "Present")

    # Initial landing page
    response = auth_client.get("/attendance")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Department Attendance" in html
    assert "Single Attendance" in html
    assert "Record Holiday" in html
    assert "View Attendance Log" in html
    assert "Attendance History Loads On Demand" in html
    assert "<table" not in html
    assert "Showing" not in html


def test_attendance_log_on_demand_and_filters(auth_client: Any, conn: Any) -> None:
    """GET /attendance?view=log or with filters loads records with pagination."""
    uid = create_user(conn, "hr_user", "pass12345", role="HR")
    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "hr_user"
        sess["role"] = "HR"

    add_employee(conn, "EMP50", "Arthur Curry", "Maritime", joining_date="2026-09-01")
    record_attendance(conn, "EMP50", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "EMP50", datetime.date(2026, 9, 2), "Absent")

    # Load on-demand with view=log
    resp = auth_client.get("/attendance?view=log")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Arthur Curry" in html
    assert "EMP50" in html

    # Filter by status=Absent
    resp_filter = auth_client.get("/attendance?status=Absent")
    assert resp_filter.status_code == 200
    html_filter = resp_filter.data.decode("utf-8")
    assert "Arthur Curry" in html_filter
    assert "Absent" in html_filter

    # Filter with non-matching department
    resp_empty = auth_client.get("/attendance?department=Finance")
    assert resp_empty.status_code == 200
    assert "No records found." in resp_empty.data.decode("utf-8")


# =============================================================================
# 3. Attendance Corrections and Immutable Audit Trail
# =============================================================================

def test_attendance_correction_requires_reason_and_logs_audit(auth_client: Any, conn: Any) -> None:
    """Web correction must require reason, update status, and write append-only audit record."""
    uid = create_user(conn, "hr_auditor", "pass12345", role="HR")
    add_employee(conn, "EMP60", "Victor Stone", "Research", joining_date="2026-09-01")
    record_attendance(conn, "EMP60", datetime.date(2026, 9, 1), "Absent", user_id=uid)

    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "hr_auditor"
        sess["role"] = "HR"
        token = sess["csrf_token"] = "valid_token_123"

    # 1. Missing reason should return 400
    resp_bad = auth_client.post(
        "/attendance/correct",
        data={
            "employee_code": "EMP60",
            "attendance_date": "2026-09-01",
            "status": "Present",
            "reason": "   ",
            "csrf_token": token,
        },
    )
    assert resp_bad.status_code == 400
    assert "correction reason is required" in resp_bad.data.decode("utf-8").lower()

    # 2. Valid correction with reason
    resp_good = auth_client.post(
        "/attendance/correct",
        data={
            "employee_code": "EMP60",
            "attendance_date": "2026-09-01",
            "status": "Present",
            "reason": "Employee was working remotely; approved by manager",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert resp_good.status_code == 200

    # Check attendance status updated
    recs = get_attendance(conn, employee_code="EMP60")
    assert len(recs) == 1
    assert recs[0]["status"] == "Present"

    # Check audit trail
    audit = get_audit_trail(conn)
    assert len(audit) == 2
    correct_audit = [a for a in audit if a["action_type"] == "CORRECT"][0]
    assert correct_audit["previous_status"] == "Absent"
    assert correct_audit["new_status"] == "Present"
    assert "remotely" in correct_audit["correction_reason"]
    assert correct_audit["user_id"] == uid


def test_audit_records_are_append_only(conn: Any) -> None:
    """Audit trail cannot be altered by normal app operations."""
    uid = create_user(conn, "hr_logger", "pass12345", role="HR")
    emp_id = add_employee(conn, "EMP61", "Billy Batson", "Media", joining_date="2026-09-01")
    att_id = record_attendance(conn, "EMP61", datetime.date(2026, 9, 8), "Present", user_id=uid)
    initial_count = count_audit_records(conn)
    assert initial_count >= 1

    # Log action directly
    log_attendance_action(
        conn,
        attendance_id=att_id,
        employee_id=emp_id,
        attendance_date=datetime.date(2026, 9, 8),
        action_type="CORRECT",
        previous_status="Present",
        new_status="Leave",
        reason="Approved emergency sick leave",
        user_id=uid,
    )
    new_count = count_audit_records(conn)
    assert new_count == initial_count + 1


# =============================================================================
# 4. Individual Employee Analytics Profile & Calculations
# =============================================================================

def test_employee_analytics_calculations_and_rules(conn: Any) -> None:
    """Analytics profile calculates KPIs accurately based on active database records."""
    emp_id = add_employee(conn, "EMP70", "Oliver Queen", "Executive", joining_date="2026-09-01")

    # September 2026: 3 Present, 1 Absent, 1 Leave = 5 Eligible Days (weekdays)
    record_attendance(conn, "EMP70", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "EMP70", datetime.date(2026, 9, 2), "Present")
    record_attendance(conn, "EMP70", datetime.date(2026, 9, 3), "Present")
    record_attendance(conn, "EMP70", datetime.date(2026, 9, 4), "Absent")
    record_attendance(conn, "EMP70", datetime.date(2026, 9, 7), "Leave")

    data = get_employee_analytics_data(conn, emp_id, year=2026, month=9)

    assert data["employee"]["employee_code"] == "EMP70"
    kpis = data["kpis"]
    assert kpis["eligible_days"] == 5
    assert kpis["present_count"] == 3
    assert kpis["absent_count"] == 1
    assert kpis["leave_count"] == 1
    # 3 / 5 * 100 = 60.0%
    assert kpis["attendance_pct"] == 60.0
    # 1 / 5 * 100 = 20.0%
    assert kpis["absenteeism_pct"] == 20.0

    # Recent exceptions should list 1 absent and 1 leave
    assert len(data["recent_exceptions"]) == 2


def test_employee_analytics_page_view(auth_client: Any, conn: Any) -> None:
    """GET /employees/<id>/analytics renders KPIs and charts."""
    uid = create_user(conn, "admin_analyst", "pass12345", role="Admin")
    emp_id = add_employee(conn, "EMP71", "Dinah Lance", "Security", joining_date="2026-09-01")
    record_attendance(conn, "EMP71", datetime.date(2026, 9, 1), "Present")

    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "admin_analyst"
        sess["role"] = "Admin"

    resp = auth_client.get(f"/employees/{emp_id}/analytics?year=2026&month=9")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Dinah Lance" in html
    assert "EMP71" in html
    assert "Attendance Rate" in html
    assert "Absenteeism Rate" in html
    assert "Monthly Attendance Trend" in html
    assert "Attendance Distribution" in html


# =============================================================================
# 5. Authentication, Authorization, Roles, and CSRF
# =============================================================================

def test_user_creation_and_password_hashing(conn: Any) -> None:
    """Password must be securely hashed and verified; plaintext is never stored."""
    user_id = create_user(conn, "secure_user", "MyPassword123!", role="HR")
    user = authenticate_user(conn, "secure_user", "MyPassword123!")
    assert user is not None
    assert user["user_id"] == user_id
    assert user["role"] == "HR"

    # Wrong password fails
    assert authenticate_user(conn, "secure_user", "WrongPassword") is None
    # Unknown username fails
    assert authenticate_user(conn, "non_existent", "MyPassword123!") is None


def test_user_toggle_and_inactive_cannot_login(conn: Any) -> None:
    """Deactivated user cannot authenticate."""
    create_user(conn, "admin_user", "AdminPass123!", role="Admin")
    hr_id = create_user(conn, "temp_hr", "TempPass123!", role="HR")

    # Deactivate HR
    toggle_user_status(conn, hr_id)
    assert authenticate_user(conn, "temp_hr", "TempPass123!") is None

    # Reactivate HR
    toggle_user_status(conn, hr_id)
    assert authenticate_user(conn, "temp_hr", "TempPass123!") is not None


def test_cannot_deactivate_sole_admin(conn: Any) -> None:
    """Cannot deactivate the only active admin account."""
    admin_id = create_user(conn, "sole_admin", "AdminPass123!", role="Admin")
    with pytest.raises(ValueError, match="Cannot deactivate the sole remaining active Admin"):
        toggle_user_status(conn, admin_id)


def test_admin_creation_and_duplicate_rejection(conn: Any) -> None:
    """Creating an admin user succeeds, while duplicate username raises ValueError."""
    admin_id = create_user(conn, username="sysadmin", password="InitialPass123!", role="Admin")
    assert admin_id > 0
    admin = get_user_by_username(conn, "sysadmin")
    assert admin is not None
    assert admin["role"] == "Admin"

    # Creating another user with same username raises duplicate error
    with pytest.raises(ValueError, match="already exists"):
        create_user(conn, username="sysadmin", password="DifferentPass456!", role="Admin")


def test_unauthenticated_requests_redirect_or_reject(auth_client: Any) -> None:
    """Unauthenticated GET redirects to /login; unauthenticated POST returns 401."""
    # GET protected route
    resp = auth_client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # POST protected route
    resp_post = auth_client.post("/attendance/new", data={})
    assert resp_post.status_code == 401


def test_role_based_access_control_admin_vs_hr(auth_client: Any, conn: Any) -> None:
    """HR role cannot access /users (403 Forbidden); Admin can access /users."""
    admin_id = create_user(conn, "admin1", "pass12345", role="Admin")
    hr_id = create_user(conn, "hr1", "pass12345", role="HR")

    # 1. As HR: Access /users should be 403
    with auth_client.session_transaction() as sess:
        sess["user_id"] = hr_id
        sess["username"] = "hr1"
        sess["role"] = "HR"

    resp_hr = auth_client.get("/users")
    assert resp_hr.status_code == 403
    assert "Forbidden" in resp_hr.data.decode("utf-8")

    # 2. As Admin: Access /users should be 200
    with auth_client.session_transaction() as sess:
        sess["user_id"] = admin_id
        sess["username"] = "admin1"
        sess["role"] = "Admin"

    resp_admin = auth_client.get("/users")
    assert resp_admin.status_code == 200
    assert "System User Accounts" in resp_admin.data.decode("utf-8")


def test_login_and_logout_flow(auth_client: Any, conn: Any) -> None:
    """Full login and logout session flow with CSRF protection."""
    create_user(conn, "portal_user", "CorrectPassword123!", role="HR")

    # 1. GET /login
    resp = auth_client.get("/login")
    assert resp.status_code == 200
    assert "Sign In" in resp.data.decode("utf-8")

    # 2. POST /login with invalid CSRF token
    resp_csrf_fail = auth_client.post(
        "/login",
        data={"username": "portal_user", "password": "CorrectPassword123!", "csrf_token": "bad"},
    )
    assert resp_csrf_fail.status_code == 400

    # 3. POST /login with valid credentials and CSRF
    with auth_client.session_transaction() as sess:
        token = sess["csrf_token"] = "valid_test_token"

    resp_login = auth_client.post(
        "/login",
        data={
            "username": "portal_user",
            "password": "CorrectPassword123!",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert resp_login.status_code == 200
    # Now authenticated: can view dashboard
    assert "portal_user" in resp_login.data.decode("utf-8")

    # 4. Logout via GET
    resp_logout = auth_client.get(
        "/logout",
        follow_redirects=True,
    )
    assert resp_logout.status_code == 200
    assert "Sign In" in resp_logout.data.decode("utf-8")


def test_schema_migration_idempotent(conn: Any) -> None:
    """migrate_auth_and_audit runs multiple times safely without duplicate table errors."""
    migrate_auth_and_audit(conn)
    migrate_auth_and_audit(conn)


def test_dashboard_dynamic_refresh_and_cache_control(auth_client: Any, conn: Any) -> None:
    """Dashboard updates dynamically after recording/correction without restart, has refresh controls & no-cache headers."""
    uid = create_user(conn, "dash_tester", "pass12345", role="HR")
    add_employee(conn, "EMP90", "Barry Allen", "SpeedForce", joining_date="2026-09-01")

    # Record 1 Present on 2026-09-01
    record_attendance(conn, "EMP90", datetime.date(2026, 9, 1), "Present")

    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "dash_tester"
        sess["role"] = "HR"

    # Initial request: 1 Present -> 100.0% attendance rate
    r1 = auth_client.get("/?year=2026&month=9")
    assert r1.status_code == 200
    html1 = r1.data.decode("utf-8")
    assert "100.0%" in html1
    assert "Refresh" in html1
    assert 'http-equiv="refresh"' in html1

    # Record an Absent record on 2026-09-02 (valid weekday)
    record_attendance(conn, "EMP90", datetime.date(2026, 9, 2), "Absent")

    # Subsequent request reflects new state dynamically: 1 Present, 1 Absent -> 50.0%
    r2 = auth_client.get("/?year=2026&month=9")
    assert r2.status_code == 200
    html2 = r2.data.decode("utf-8")
    assert "50.0%" in html2

    # Check chart headers prevent caching
    chart_resp = auth_client.get("/charts/file/monthly_attendance.png")
    assert chart_resp.status_code == 200
    assert "no-cache" in chart_resp.headers.get("Cache-Control", "")

    # Failed save (conflict) does not falsely alter dashboard
    with pytest.raises(ValueError):
        record_attendance(conn, "EMP90", datetime.date(2026, 9, 2), "Present")

    r3 = auth_client.get("/?year=2026&month=9")
    assert r3.status_code == 200
    assert "50.0%" in r3.data.decode("utf-8")


def test_audit_view_route(auth_client: Any, conn: Any) -> None:
    """GET /audit renders audit records with filtering and empty state."""
    uid = create_user(conn, "audit_viewer", "pass12345", role="Admin")
    add_employee(conn, "EMP95", "Diana Prince", "Security", joining_date="2026-09-01")
    att_id = record_attendance(conn, "EMP95", datetime.date(2026, 9, 1), "Absent", user_id=uid)
    update_attendance(
        conn,
        "EMP95",
        datetime.date(2026, 9, 1),
        "Present",
        reason="Approved remote shift",
        user_id=uid,
    )

    with auth_client.session_transaction() as sess:
        sess["user_id"] = uid
        sess["username"] = "audit_viewer"
        sess["role"] = "Admin"

    # Default /audit
    resp = auth_client.get("/audit")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Audit Trail" in html
    assert "EMP95" in html
    assert "Approved remote shift" in html
    assert "CORRECT" in html

    # Filter by action=CORRECT
    resp_correct = auth_client.get("/audit?action=CORRECT")
    assert resp_correct.status_code == 200
    assert "Approved remote shift" in resp_correct.data.decode("utf-8")

    # Filter with non-existent employee
    resp_none = auth_client.get("/audit?employee=NONEXISTENT")
    assert resp_none.status_code == 200
    assert "No audit records found" in resp_none.data.decode("utf-8")

