"""Tests for Flask forms and data modifications (Phase W2)."""

import datetime
from pathlib import Path
import re
from typing import Any
import pytest
import config
from src.attendance import get_attendance, record_attendance
from src.employees import add_employee, deactivate_employee, get_employee, list_employees
from src.web import create_app


@pytest.fixture
def app(tmp_path: Path) -> Any:
    """Create a Flask application instance configured for testing."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE_NAME": config.DB_TEST_NAME,
            "OUTPUT_DIR": str(tmp_path),
        }
    )


@pytest.fixture
def client(app: Any) -> Any:
    """Provide a test client for the configured application."""
    return app.test_client()


@pytest.fixture(autouse=True)
def setup_conn(conn: Any) -> None:
    """Ensure conn sees transactions committed by the web client."""
    conn.autocommit = True


def get_csrf_token(client: Any, url: str) -> str:
    """Perform a GET request to url and extract the hidden csrf_token input value."""
    response = client.get(url)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html)
    assert match is not None, f"csrf_token not found in response from {url}"
    return match.group(1)


def test_csrf_protection_and_flow(client: Any, conn: Any) -> None:
    """Test CSRF token requirement on POST and successful submission flow."""
    # GET /employees/new contains hidden csrf_token input
    token = get_csrf_token(client, "/employees/new")
    assert token

    # POST with no token returns 400 and adds nothing
    res_no_token = client.post(
        "/employees/new",
        data={
            "employee_code": "E001",
            "employee_name": "Asha Sharma",
            "department": "Engineering",
        },
    )
    assert res_no_token.status_code == 400
    assert "Error: invalid or missing form token." in res_no_token.get_data(as_text=True)
    assert get_employee(conn, "E001") is None

    # POST with wrong token returns 400 and adds nothing
    res_wrong_token = client.post(
        "/employees/new",
        data={
            "csrf_token": "wrong-token-value-here",
            "employee_code": "E001",
            "employee_name": "Asha Sharma",
            "department": "Engineering",
        },
    )
    assert res_wrong_token.status_code == 400
    assert "Error: invalid or missing form token." in res_wrong_token.get_data(as_text=True)
    assert get_employee(conn, "E001") is None

    # POST with right token returns 302 to /employees
    token = get_csrf_token(client, "/employees/new")
    res_ok = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "employee_name": "Asha Sharma",
            "department": "Engineering",
        },
    )
    assert res_ok.status_code == 302
    assert res_ok.headers.get("Location") == "/employees"
    assert get_employee(conn, "E001") is not None

    # Following the redirect shows "Employee E001 added." and the row
    redirect_res = client.get("/employees")
    assert redirect_res.status_code == 200
    html = redirect_res.get_data(as_text=True)
    assert "Employee E001 added." in html
    assert "E001" in html


def test_post_unknown_url_and_method_not_allowed(client: Any) -> None:
    """POST to unknown URL returns 404, and POST to GET-only route returns 405."""
    res_404 = client.post("/unknown-url-without-token")
    assert res_404.status_code == 404

    res_405 = client.post("/employees")
    assert res_405.status_code == 405


def test_employee_validation_duplicate_and_blank(client: Any, conn: Any) -> None:
    """Test duplicate employee code rejection and blank name rejection."""
    token = get_csrf_token(client, "/employees/new")
    res1 = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "employee_name": "Asha Sharma",
            "department": "Engineering",
        },
    )
    assert res1.status_code == 302

    # Duplicate code returns 400 with "Error:" and only 1 row exists
    token = get_csrf_token(client, "/employees/new")
    res_dup = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "employee_name": "Ravi Kumar",
            "department": "Marketing",
        },
    )
    assert res_dup.status_code == 400
    assert "Error:" in res_dup.get_data(as_text=True)
    all_emps = list_employees(conn, include_inactive=True)
    assert len(all_emps) == 1

    # Blank name returns 400 and nothing added
    token = get_csrf_token(client, "/employees/new")
    res_blank = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E002",
            "employee_name": "   ",
            "department": "Marketing",
        },
    )
    assert res_blank.status_code == 400
    assert "Error:" in res_blank.get_data(as_text=True)
    all_emps = list_employees(conn, include_inactive=True)
    assert len(all_emps) == 1


def test_employee_name_xss_storage_and_escaping(client: Any, conn: Any) -> None:
    """XSS string is stored unescaped in DB but escaped in rendered HTML."""
    xss_payload = "<script>alert(1)</script>"
    token = get_csrf_token(client, "/employees/new")
    res = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E099",
            "employee_name": xss_payload,
            "department": "Security",
        },
    )
    assert res.status_code == 302
    emp = get_employee(conn, "E099")
    assert emp is not None
    assert emp["employee_name"] == xss_payload

    list_res = client.get("/employees")
    assert list_res.status_code == 200
    html = list_res.get_data(as_text=True)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert xss_payload not in html


def test_edit_employee_flow(client: Any, conn: Any) -> None:
    """Test editing an existing employee and input validation."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")

    # Success edit
    token = get_csrf_token(client, "/employees/E001/edit")
    res = client.post(
        "/employees/E001/edit",
        data={
            "csrf_token": token,
            "employee_name": "Asha Sharma",
            "department": "Sales",
        },
    )
    assert res.status_code == 302
    emp = get_employee(conn, "E001")
    assert emp is not None
    assert emp["department"] == "Sales"

    # Blank department returns 400 and department remains unchanged
    token = get_csrf_token(client, "/employees/E001/edit")
    res_blank = client.post(
        "/employees/E001/edit",
        data={
            "csrf_token": token,
            "employee_name": "Asha Sharma",
            "department": "   ",
        },
    )
    assert res_blank.status_code == 400
    assert "Error:" in res_blank.get_data(as_text=True)
    emp_after = get_employee(conn, "E001")
    assert emp_after is not None
    assert emp_after["department"] == "Sales"

    # Unknown code returns 404
    assert client.get("/employees/NONEXISTENT/edit").status_code == 404
    token = get_csrf_token(client, "/employees/new")
    assert (
        client.post(
            "/employees/NONEXISTENT/edit",
            data={
                "csrf_token": token,
                "employee_name": "Ghost",
                "department": "Sales",
            },
        ).status_code
        == 404
    )


def test_deactivate_employee_flow(client: Any, conn: Any) -> None:
    """Test deactivation confirmation, cancellation, and execution."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")

    # GET confirmation page
    get_res = client.get("/employees/E001/deactivate")
    assert get_res.status_code == 200
    html = get_res.get_data(as_text=True)
    assert "Deactivate E001 - Asha Sharma? This cannot be undone from the website." in html
    assert "Type YES to confirm" in html

    # Unknown code returns 404
    assert client.get("/employees/UNKNOWN/deactivate").status_code == 404
    token = get_csrf_token(client, "/employees/E001/deactivate")
    assert (
        client.post(
            "/employees/UNKNOWN/deactivate",
            data={"csrf_token": token, "confirm": "YES"},
        ).status_code
        == 404
    )

    # Confirm "no" leaves active
    token = get_csrf_token(client, "/employees/E001/deactivate")
    res_no = client.post(
        "/employees/E001/deactivate",
        data={"csrf_token": token, "confirm": "no"},
    )
    assert res_no.status_code == 302
    emp = get_employee(conn, "E001")
    assert emp is not None and emp["is_active"] is True

    # Confirm "yes" (lowercase) leaves active
    token = get_csrf_token(client, "/employees/E001/deactivate")
    res_lower = client.post(
        "/employees/E001/deactivate",
        data={"csrf_token": token, "confirm": "yes"},
    )
    assert res_lower.status_code == 302
    emp = get_employee(conn, "E001")
    assert emp is not None and emp["is_active"] is True

    # Confirm "YES" deactivates employee
    token = get_csrf_token(client, "/employees/E001/deactivate")
    res_yes = client.post(
        "/employees/E001/deactivate",
        data={"csrf_token": token, "confirm": "YES"},
    )
    assert res_yes.status_code == 302
    emp = get_employee(conn, "E001")
    assert emp is not None and emp["is_active"] is False

    # Check Actions column in /employees
    add_employee(conn, "E002", "Ravi Kumar", "Marketing")
    res_list = client.get("/employees?include_inactive=1")
    assert res_list.status_code == 200
    list_html = res_list.get_data(as_text=True)
    assert "/employees/E002/edit" in list_html
    assert "/employees/E002/deactivate" in list_html
    assert "/employees/E001/edit" not in list_html
    assert "/employees/E001/deactivate" not in list_html


def test_record_attendance_flow(client: Any, conn: Any) -> None:
    """Test recording daily attendance with diverse valid and invalid inputs."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")
    add_employee(conn, "E002", "Inactive Emp", "Engineering")
    deactivate_employee(conn, "E002")

    # Valid POST
    token = get_csrf_token(client, "/attendance/new")
    res = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-01",
            "status": "Present",
        },
    )
    assert res.status_code == 302
    rows = get_attendance(conn, "E001")
    assert len(rows) == 1

    # Second identical POST returns 400 and still 1 row
    token = get_csrf_token(client, "/attendance/new")
    res_dup = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-01",
            "status": "Present",
        },
    )
    assert res_dup.status_code == 400
    assert len(get_attendance(conn, "E001")) == 1

    # Saturday 2026-09-05 returns 400 and no row
    token = get_csrf_token(client, "/attendance/new")
    res_sat = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-05",
            "status": "Present",
        },
    )
    assert res_sat.status_code == 400
    assert len(get_attendance(conn, "E001")) == 1

    # Date 2026-13-45 returns 400
    token = get_csrf_token(client, "/attendance/new")
    res_bad_date = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-13-45",
            "status": "Present",
        },
    )
    assert res_bad_date.status_code == 400
    assert len(get_attendance(conn, "E001")) == 1

    # Status Sick returns 400
    token = get_csrf_token(client, "/attendance/new")
    res_sick = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-02",
            "status": "Sick",
        },
    )
    assert res_sick.status_code == 400
    assert len(get_attendance(conn, "E001")) == 1

    # Inactive employee returns 400
    token = get_csrf_token(client, "/attendance/new")
    res_inact = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E002",
            "attendance_date": "2026-09-02",
            "status": "Present",
        },
    )
    assert res_inact.status_code == 400
    assert len(get_attendance(conn, "E002")) == 0

    # Unknown employee returns 400
    token = get_csrf_token(client, "/attendance/new")
    res_unk = client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E999",
            "attendance_date": "2026-09-02",
            "status": "Present",
        },
    )
    assert res_unk.status_code == 400


def test_correct_attendance_flow(client: Any, conn: Any) -> None:
    """Test modifying existing attendance records."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")

    # Present to Absent works
    token = get_csrf_token(client, "/attendance/correct")
    res = client.post(
        "/attendance/correct",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-01",
            "status": "Absent",
        },
    )
    assert res.status_code == 302
    rows = get_attendance(conn, "E001")
    assert len(rows) == 1
    assert rows[0]["status"] == "Absent"

    # Correcting date with no record returns 400
    token = get_csrf_token(client, "/attendance/correct")
    res_none = client.post(
        "/attendance/correct",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-02",
            "status": "Present",
        },
    )
    assert res_none.status_code == 400


def test_record_holiday_flow(client: Any, conn: Any) -> None:
    """Test holiday insertion for active staff and error validation."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Marketing")
    add_employee(conn, "E003", "Charlie Inactive", "HR")
    deactivate_employee(conn, "E003")

    # 2 active employees, POST 2026-09-10 (Thursday)
    token = get_csrf_token(client, "/holidays/new")
    res = client.post(
        "/holidays/new",
        data={"csrf_token": token, "holiday_date": "2026-09-10"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Holiday recorded for 2 employees." in res.get_data(as_text=True)
    all_att = get_attendance(conn, start_date=datetime.date(2026, 9, 10), end_date=datetime.date(2026, 9, 10))
    assert len(all_att) == 2
    for r in all_att:
        assert r["status"] == "Holiday"

    # Saturday returns 400
    token = get_csrf_token(client, "/holidays/new")
    res_sat = client.post(
        "/holidays/new",
        data={"csrf_token": token, "holiday_date": "2026-09-12"},
    )
    assert res_sat.status_code == 400

    # Conflict on that date returns 400 and creates no rows
    record_attendance(conn, "E001", datetime.date(2026, 9, 15), "Present")
    token = get_csrf_token(client, "/holidays/new")
    res_conflict = client.post(
        "/holidays/new",
        data={"csrf_token": token, "holiday_date": "2026-09-15"},
    )
    assert res_conflict.status_code == 400
    e002_rows = get_attendance(conn, "E002", start_date=datetime.date(2026, 9, 15), end_date=datetime.date(2026, 9, 15))
    assert len(e002_rows) == 0


def test_report_reflects_recorded_attendance(client: Any, conn: Any) -> None:
    """Monthly report reflects changes from attendance entries and corrections."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")

    # Record 2026-09-01 as Present
    token = get_csrf_token(client, "/attendance/new")
    client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-01",
            "status": "Present",
        },
    )

    # Record 2026-09-02 initially as Present
    token = get_csrf_token(client, "/attendance/new")
    client.post(
        "/attendance/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-02",
            "status": "Present",
        },
    )

    # Correct 2026-09-02 to Absent
    token = get_csrf_token(client, "/attendance/correct")
    client.post(
        "/attendance/correct",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "attendance_date": "2026-09-02",
            "status": "Absent",
        },
    )

    # Check monthly report: 1 Present, 1 Absent out of 2 eligible = 50.00%
    report_res = client.get("/report?year=2026&month=9")
    assert report_res.status_code == 200
    report_text = report_res.get_data(as_text=True)
    assert "Overall attendance: 50.00%" in report_text


def test_http_methods_and_forbidden_rules(client: Any, app: Any) -> None:
    """PUT and DELETE on /employees/new return 405; app.url_map has no DELETE or 'delete' rule."""
    assert client.put("/employees/new").status_code == 405
    assert client.delete("/employees/new").status_code == 405

    for rule in app.url_map.iter_rules():
        assert "DELETE" not in rule.methods, f"Rule {rule} allows DELETE method"
        assert "delete" not in rule.rule.lower(), f"Rule {rule} path contains 'delete'"


def test_security_headers_on_responses(client: Any, conn: Any) -> None:
    """Security headers are present on successful POST (302) and 400 error responses."""
    # 400 error response
    res_400 = client.post("/employees/new", data={})
    assert res_400.status_code == 400
    assert res_400.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_400.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in res_400.headers

    # 302 success response
    token = get_csrf_token(client, "/employees/new")
    res_302 = client.post(
        "/employees/new",
        data={
            "csrf_token": token,
            "employee_code": "E001",
            "employee_name": "Asha Sharma",
            "department": "Engineering",
        },
    )
    assert res_302.status_code == 302
    assert res_302.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_302.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in res_302.headers


def test_department_attendance_page_get(client: Any, conn: Any) -> None:
    """GET /attendance/department renders department selection and loads eligible roster."""
    add_employee(conn, "E060", "Roster One", "Engineering", joining_date="2026-09-01")
    add_employee(conn, "E061", "Roster Two", "Engineering", joining_date="2026-09-01")

    # Initial page without department
    res = client.get("/attendance/department")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Department Bulk Attendance" in html
    assert "Engineering" in html

    # With department and valid date
    res_roster = client.get(
        "/attendance/department?department=Engineering&attendance_date=2026-09-08"
    )
    assert res_roster.status_code == 200
    html_roster = res_roster.get_data(as_text=True)
    assert "E060" in html_roster
    assert "E061" in html_roster
    assert "Department Attendance Roster" in html_roster
    assert "Mark All Present" in html_roster


def test_department_attendance_get_duplicate_warning(client: Any, conn: Any) -> None:
    """GET /attendance/department shows duplicate conflict alert if attendance already exists."""
    add_employee(conn, "E062", "Existing Emp", "Support", joining_date="2026-09-01")
    record_attendance(conn, "E062", datetime.date(2026, 9, 8), "Present")

    res = client.get(
        "/attendance/department?department=Support&attendance_date=2026-09-08"
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Duplicate Attendance Detected" in html
    assert "E062" in html
    assert "Existing Emp" in html
    assert "/attendance/correct" in html


def test_department_attendance_post_csrf(client: Any, conn: Any) -> None:
    """POST /attendance/department requires valid CSRF token."""
    add_employee(conn, "E063", "Csrf Tester", "Legal", joining_date="2026-09-01")

    # Missing token returns 400
    res_no_token = client.post(
        "/attendance/department",
        data={
            "department": "Legal",
            "attendance_date": "2026-09-08",
            "employee_codes": ["E063"],
            "status_E063": "Present",
        },
    )
    assert res_no_token.status_code == 400
    assert "Error: invalid or missing form token." in res_no_token.get_data(as_text=True)


def test_department_attendance_post_success(client: Any, conn: Any) -> None:
    """POST /attendance/department saves entire batch atomically and redirects."""
    add_employee(conn, "E064", "Batch One", "Operations", joining_date="2026-09-01")
    add_employee(conn, "E065", "Batch Two", "Operations", joining_date="2026-09-01")

    token = get_csrf_token(
        client,
        "/attendance/department?department=Operations&attendance_date=2026-09-08",
    )
    res = client.post(
        "/attendance/department",
        data={
            "csrf_token": token,
            "department": "Operations",
            "attendance_date": "2026-09-08",
            "employee_codes": ["E064", "E065"],
            "status_E064": "Present",
            "status_E065": "Leave",
            "confirm_review": "on",
        },
    )
    assert res.status_code == 302
    assert "/attendance" in res.headers.get("Location", "")

    # Check database records
    e064_rows = get_attendance(conn, employee_code="E064")
    assert len(e064_rows) == 1
    assert e064_rows[0]["status"] == "Present"

    e065_rows = get_attendance(conn, employee_code="E065")
    assert len(e065_rows) == 1
    assert e065_rows[0]["status"] == "Leave"


def test_department_attendance_post_conflict_rejection_and_rollback(
    client: Any, conn: Any
) -> None:
    """POST /attendance/department rejects entire batch when any conflict exists."""
    add_employee(conn, "E066", "QA One", "QA", joining_date="2026-09-01")
    add_employee(conn, "E067", "QA Two", "QA", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    # Record attendance for E066 beforehand
    record_attendance(conn, "E066", att_date, "Present")

    token = get_csrf_token(
        client, f"/attendance/department?department=QA&attendance_date={att_date}"
    )
    res = client.post(
        "/attendance/department",
        data={
            "csrf_token": token,
            "department": "QA",
            "attendance_date": str(att_date),
            "employee_codes": ["E066", "E067"],
            "status_E066": "Present",
            "status_E067": "Present",
            "confirm_review": "on",
        },
    )
    assert res.status_code == 400
    html = res.get_data(as_text=True)
    assert "Attendance already recorded for 1 employee(s)" in html
    assert "E066" in html

    # Verify atomic rollback: E067 has no row saved
    assert len(get_attendance(conn, employee_code="E067")) == 0


def test_department_attendance_post_weekend_and_invalid_date(
    client: Any, conn: Any
) -> None:
    """POST /attendance/department rejects weekend dates and malformed date strings."""
    add_employee(conn, "E068", "Weekend Tester", "HR", joining_date="2026-09-01")

    token = get_csrf_token(client, "/attendance/department")
    res_weekend = client.post(
        "/attendance/department",
        data={
            "csrf_token": token,
            "department": "HR",
            "attendance_date": "2026-09-05",  # Saturday
            "employee_codes": ["E068"],
            "status_E068": "Present",
        },
    )
    assert res_weekend.status_code == 400
    assert "cannot be recorded on weekends" in res_weekend.get_data(as_text=True)

    token = get_csrf_token(client, "/attendance/department")
    res_bad_date = client.post(
        "/attendance/department",
        data={
            "csrf_token": token,
            "department": "HR",
            "attendance_date": "2026-13-45",
            "employee_codes": ["E068"],
            "status_E068": "Present",
        },
    )
    assert res_bad_date.status_code == 400
    assert "Invalid date" in res_bad_date.get_data(as_text=True)


def test_attendance_log_enhancements(client: Any, conn: Any) -> None:
    """Attendance log displays employee names, department filter, and correction links."""
    add_employee(conn, "E070", "John Doe", "Sales", joining_date="2026-09-01")
    add_employee(conn, "E071", "Jane Smith", "Finance", joining_date="2026-09-01")
    att_date = datetime.date(2026, 9, 8)

    record_attendance(conn, "E070", att_date, "Present")
    record_attendance(conn, "E071", att_date, "Present")

    # Explicit attendance log view
    res = client.get("/attendance?view=log")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "John Doe" in html
    assert "Jane Smith" in html
    assert "/attendance/department" in html
    assert "employee_code=E070" in html
    assert "Correct" in html

    # Filter by department
    res_dept = client.get("/attendance?department=Sales")
    assert res_dept.status_code == 200
    html_dept = res_dept.get_data(as_text=True)
    assert "E070" in html_dept
    assert "John Doe" in html_dept
    assert "E071" not in html_dept


def test_attendance_form_datalist_and_prepopulation(client: Any, conn: Any) -> None:
    """Attendance form provides searchable datalist and pre-populates query arguments."""
    add_employee(conn, "E072", "Mark Taylor", "HR", joining_date="2026-09-01")

    # /attendance/new includes datalist with active employee
    res_new = client.get("/attendance/new")
    assert res_new.status_code == 200
    html_new = res_new.get_data(as_text=True)
    assert 'list="employee_options"' in html_new
    assert "E072" in html_new

    # /attendance/correct pre-populates employee_code and attendance_date
    res_correct = client.get(
        "/attendance/correct?employee_code=E072&attendance_date=2026-09-08"
    )
    assert res_correct.status_code == 200
    html_correct = res_correct.get_data(as_text=True)
    assert 'value="E072"' in html_correct
    assert 'value="2026-09-08"' in html_correct


def test_session_cookie_flags(client: Any) -> None:

    """Session cookie after GET of form page includes HttpOnly and SameSite=Lax."""
    res = client.get("/employees/new")
    assert res.status_code == 200
    set_cookie = res.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie


def test_web_source_security_and_architectural_rules() -> None:
    """Verify code safety constraints in web source files."""
    web_dir = Path("src/web")
    py_files = list(web_dir.rglob("*.py"))
    assert py_files, "No python files found under src/web"

    sql_words = ["SELECT", "INSERT", "UPDATE", "DELETE"]
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        for word in sql_words:
            assert word not in content, f"Found '{word}' in {py_file}"

    all_web_files = list(web_dir.rglob("*"))
    for file_path in all_web_files:
        if file_path.is_file():
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            assert "|safe" not in content, f"Found '|safe' in {file_path}"
            assert "Markup" not in content, f"Found 'Markup' in {file_path}"

    template_files = list((web_dir / "templates").glob("*.html"))
    assert template_files, "No template files found under src/web/templates"
    for tmpl in template_files:
        content = tmpl.read_text(encoding="utf-8")
        assert "<script" not in content.lower(), f"Found '<script' in template {tmpl}"

    init_content = (web_dir / "__init__.py").read_text(encoding="utf-8")
    assert "compare_digest" in init_content


def test_active_nav_indicators(client: Any) -> None:
    """Verify that active navigation indicators highlight the appropriate hub."""
    res_dash = client.get("/")
    assert res_dash.status_code == 200
    assert 'href="/" class="active">Dashboard</a>' in res_dash.get_data(as_text=True)

    res_emp = client.get("/employees")
    assert res_emp.status_code == 200
    assert 'href="/employees" class="active">Employees</a>' in res_emp.get_data(as_text=True)

    res_att = client.get("/attendance")
    assert res_att.status_code == 200
    assert 'href="/attendance" class="active">Attendance</a>' in res_att.get_data(as_text=True)

    res_rep = client.get("/summary/employees")
    assert res_rep.status_code == 200
    assert 'href="/summary/employees" class="active">Reports</a>' in res_rep.get_data(as_text=True)


def test_searchable_selectors_rich_options(client: Any, conn: Any) -> None:
    """Verify searchable selector presents code, name, department and selected staff card."""
    add_employee(conn, "E099", "Nina Patel", "Marketing", joining_date="2026-09-01")

    res_new = client.get("/attendance/new")
    assert res_new.status_code == 200
    html_new = res_new.get_data(as_text=True)
    assert 'list="employee_options"' in html_new
    assert "E099" in html_new
    assert "Nina Patel" in html_new
    assert "Marketing" in html_new

    res_correct = client.get("/attendance/correct?employee_code=E099&attendance_date=2026-09-08")
    assert res_correct.status_code == 200
    html_correct = res_correct.get_data(as_text=True)
    assert "Selected:" in html_correct
    assert "Nina Patel" in html_correct
    assert "Marketing" in html_correct


def test_report_subnav_and_defaults(client: Any) -> None:
    """Verify default query parameters on reports/charts and subnav active state."""
    res_rep = client.get("/report")
    assert res_rep.status_code == 200
    html_rep = res_rep.get_data(as_text=True)
    assert "2026-09" in html_rep
    assert 'href="/report?year=2026&month=9" class="btn btn-primary' in html_rep

    res_charts = client.get("/charts")
    assert res_charts.status_code == 200
    html_charts = res_charts.get_data(as_text=True)
    assert "2026-09" in html_charts
    assert 'href="/charts?year=2026&month=9" class="btn btn-primary' in html_charts

