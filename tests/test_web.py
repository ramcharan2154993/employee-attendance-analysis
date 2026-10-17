"""Tests for Flask web interface (Phase W1)."""

import datetime
from pathlib import Path
import re
from typing import Any
import pytest
import config
from src.attendance import record_attendance
from src.employees import add_employee, deactivate_employee
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


@pytest.fixture
def sample_data(conn: Any) -> None:
    """Populate test database with known employees and attendance records."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Marketing")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Absent")
    record_attendance(conn, "E002", datetime.date(2026, 9, 1), "Present")
    deactivate_employee(conn, "E002")
    add_employee(conn, "E003", "Karan Patel", "Engineering")


def test_create_app_testing_with_main_database_raises_value_error() -> None:
    """create_app with TESTING true and DATABASE_NAME 'attendance_db' must raise ValueError."""
    with pytest.raises(ValueError):
        create_app(
            {
                "TESTING": True,
                "DATABASE_NAME": "attendance_db",
                "SECRET_KEY": "test-secret",
            }
        )


def test_create_app_missing_secret_key_raises_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_app without a secret key (TESTING false, SECRET_KEY empty) must raise RuntimeError."""
    monkeypatch.setattr(config, "FLASK_SECRET_KEY", None)
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY is not set in .env"):
        create_app({"TESTING": False, "SECRET_KEY": ""})


def test_index_dashboard(client: Any, app: Any) -> None:
    """GET / returns 200 and contains 'Employee Attendance Analysis System'. app.debug is False."""
    assert app.debug is False
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Employee Attendance Analysis System" in html


def test_employees_view(client: Any, sample_data: None) -> None:
    """Test /employees filtering, inactive inclusion, and search."""
    # Default page: shows E001 (active) and not E002 (deactivated)
    resp_default = client.get("/employees")
    assert resp_default.status_code == 200
    html_default = resp_default.get_data(as_text=True)
    assert "E001" in html_default
    assert "E002" not in html_default

    # include_inactive=1: shows both and the word Inactive
    resp_inactive = client.get("/employees?include_inactive=1")
    assert resp_inactive.status_code == 200
    html_inactive = resp_inactive.get_data(as_text=True)
    assert "E001" in html_inactive
    assert "E002" in html_inactive
    assert "Inactive" in html_inactive

    # q=Asha finds matching employee only
    resp_search = client.get("/employees?q=Asha")
    assert resp_search.status_code == 200
    html_search = resp_search.get_data(as_text=True)
    assert "Asha Sharma" in html_search
    assert "Ravi Kumar" not in html_search


def test_employees_xss_escaping(client: Any, conn: Any) -> None:
    """An employee named <script>alert(1)</script> appears escaped and raw script does not appear."""
    raw_tag = "<script>alert(1)</script>"
    add_employee(conn, "E099", raw_tag, "Security")
    resp = client.get("/employees")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert raw_tag not in html


def test_attendance_view(client: Any, sample_data: None) -> None:
    """Test /attendance filters, valid queries, and error handling."""
    # employee=E001 shows two rows
    resp_emp = client.get("/attendance?employee=E001")
    assert resp_emp.status_code == 200
    html_emp = resp_emp.get_data(as_text=True)
    assert html_emp.count("E001") >= 2
    assert "2026-09-01" in html_emp
    assert "2026-09-02" in html_emp

    # start=2026-09-02&end=2026-09-02 shows only the Absent row
    resp_date = client.get("/attendance?start=2026-09-02&end=2026-09-02")
    assert resp_date.status_code == 200
    html_date = resp_date.get_data(as_text=True)
    assert "Absent" in html_date
    assert "2026-09-01" not in html_date

    # Empty result shows "No records found."
    resp_empty = client.get("/attendance?start=2026-08-01&end=2026-08-05")
    assert resp_empty.status_code == 200
    assert "No records found." in resp_empty.get_data(as_text=True)

    # start=2026-13-45 returns 400 and contains "Error"
    resp_bad_date = client.get("/attendance?start=2026-13-45")
    assert resp_bad_date.status_code == 400
    assert "Error" in resp_bad_date.get_data(as_text=True)

    # start after end returns 400
    resp_order = client.get("/attendance?start=2026-09-05&end=2026-09-01")
    assert resp_order.status_code == 400
    assert "Error" in resp_order.get_data(as_text=True)

    # employee=NOPE returns 400
    resp_bad_emp = client.get("/attendance?employee=NOPE")
    assert resp_bad_emp.status_code == 400
    assert "Error" in resp_bad_emp.get_data(as_text=True)


def test_monthly_report_view(client: Any, sample_data: None) -> None:
    """Test /report metrics, percentage output, and input validation."""
    resp = client.get("/report?year=2026&month=9")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "50.00%" in body
    assert "Overall attendance: 66.67%" in body

    # month=13, month=0 and month=x each return 400
    for bad_month in ["13", "0", "x"]:
        bad_resp = client.get(f"/report?year=2026&month={bad_month}")
        assert bad_resp.status_code == 400
        assert "Error" in bad_resp.get_data(as_text=True)

    # year=2026&month=8 contains "No attendance records for 2026-08."
    resp_empty_month = client.get("/report?year=2026&month=8")
    assert resp_empty_month.status_code == 200
    assert "No attendance records for 2026-08." in resp_empty_month.get_data(as_text=True)


def test_summaries_and_ranking_views(client: Any, sample_data: None) -> None:
    """Test /summary/employees, /summary/departments, and /ranking."""
    resp_emp = client.get("/summary/employees")
    assert resp_emp.status_code == 200
    body_emp = resp_emp.get_data(as_text=True)
    assert "E001" in body_emp
    assert "N/A" in body_emp

    resp_dept = client.get("/summary/departments")
    assert resp_dept.status_code == 200
    body_dept = resp_dept.get_data(as_text=True)
    assert "Engineering" in body_dept
    assert "Marketing" in body_dept

    resp_rank = client.get("/ranking")
    assert resp_rank.status_code == 200
    body_rank = resp_rank.get_data(as_text=True)
    pos_e001 = body_rank.find("E001")
    pos_e002 = body_rank.find("E002")
    assert pos_e001 != -1 and pos_e002 != -1
    assert pos_e001 < pos_e002


def test_charts_view_and_file_serving(client: Any, sample_data: None) -> None:
    """Test /charts view and strict static file serving route."""
    resp_charts = client.get("/charts?year=2026&month=9")
    assert resp_charts.status_code == 200

    resp_file = client.get("/charts/file/monthly_attendance.png")
    assert resp_file.status_code == 200
    assert resp_file.content_type == "image/png"
    assert resp_file.data.startswith(b"\x89PNG")

    # Path traversal and invalid files must return 404
    assert client.get("/charts/file/..%2F.env").status_code == 404
    assert client.get("/charts/file/anything.png").status_code == 404


def test_post_methods_not_allowed(client: Any) -> None:
    """POST to /employees, /report and /attendance each return 405."""
    assert client.post("/employees").status_code == 405
    assert client.post("/report").status_code == 405
    assert client.post("/attendance").status_code == 405


def test_security_headers(client: Any) -> None:
    """Every response from / has X-Content-Type-Options, X-Frame-Options and Content-Security-Policy."""
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_unknown_url_returns_404(client: Any) -> None:
    """An unknown URL returns 404 and the page says 'Page not found'."""
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    assert "Page not found" in response.get_data(as_text=True)


def test_file_checks_security_and_architectural_rules() -> None:
    """Verify web codebase adheres to SQL, escaping, and template security constraints."""
    web_dir = Path("src/web")
    py_files = list(web_dir.rglob("*.py"))
    assert py_files, "No python files found under src/web"

    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE"]
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        for kw in sql_keywords:
            match = re.search(rf"\b{kw}\b", content)
            assert match is None, f"Found forbidden SQL keyword '{kw}' in {py_file}"

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
