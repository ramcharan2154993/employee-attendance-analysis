"""Comprehensive tests for Employee Analytics bug fixes and Redesigned Report Pages."""

import datetime
from pathlib import Path
import re
from typing import Any, Dict
import pytest
import config
from src.attendance import record_attendance
from src.auth import create_user
from src.employees import add_employee
from src.web import create_app


@pytest.fixture
def app(tmp_path: Path) -> Any:
    """Create a Flask application instance configured for testing."""
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-report-pages",
            "DATABASE_NAME": config.DB_TEST_NAME,
            "OUTPUT_DIR": str(tmp_path),
            "REQUIRE_AUTH": True,
        }
    )


@pytest.fixture
def client(app: Any) -> Any:
    """Provide an unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app: Any, conn: Any) -> Any:
    """Provide an authenticated test client with Admin privileges."""
    user_id = create_user(conn, "test_admin", "AdminPass123!", role="Admin")
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["username"] = "test_admin"
        sess["role"] = "Admin"
        sess["csrf_token"] = "valid_csrf_token_report_tests"
    return test_client


@pytest.fixture
def handworked_data(conn: Any) -> Dict[str, int]:
    """
    Populate database with precisely hand-worked dataset:
    Engineering department:
      E001:
        Sep 2026: 3 Present, 1 Absent (Eligible: 4, 75.00% attendance, 25.00% absenteeism)
        Oct 2026: 2 Present, 0 Absent (Eligible: 2, 100.00% attendance, 0.00% absenteeism)
        All-time: 5 Present, 1 Absent (Eligible: 6, 83.33% attendance, 16.67% absenteeism)
      E002:
        Sep 2026: 1 Present, 1 Absent (Eligible: 2, 50.00% attendance, 50.00% absenteeism)
        Oct 2026: 1 Present, 1 Absent (Eligible: 2, 50.00% attendance, 50.00% absenteeism)
        All-time: 2 Present, 2 Absent (Eligible: 4, 50.00% attendance, 50.00% absenteeism)
      Engineering Dept Benchmark:
        Sep 2026: 4 Present, 2 Absent (Eligible: 6, 66.67% attendance, 33.33% absenteeism)
        Oct 2026: 3 Present, 1 Absent (Eligible: 4, 75.00% attendance, 25.00% absenteeism)
        All-time: 7 Present, 3 Absent (Eligible: 10, 70.00% attendance, 30.00% absenteeism)
      E003:
        Zero attendance records (for empty-state handling)
    """
    conn.autocommit = True
    e1_id = add_employee(conn, "E001", "Alice Smith", "Engineering", joining_date="2026-09-01")
    e2_id = add_employee(conn, "E002", "Bob Jones", "Engineering", joining_date="2026-09-01")
    e3_id = add_employee(conn, "E003", "Charlie Brown", "Engineering", joining_date="2026-09-01")

    # E001 Attendance
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 3), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 4), "Absent")
    record_attendance(conn, "E001", datetime.date(2026, 10, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 10, 2), "Present")

    # E002 Attendance
    record_attendance(conn, "E002", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E002", datetime.date(2026, 9, 2), "Absent")
    record_attendance(conn, "E002", datetime.date(2026, 10, 1), "Present")
    record_attendance(conn, "E002", datetime.date(2026, 10, 2), "Absent")

    return {"e1_id": e1_id, "e2_id": e2_id, "e3_id": e3_id}


# =============================================================================
# 1. Bug A: Employee Analytics Period Filtering & Dropdown
# =============================================================================

def test_analytics_period_filter_october(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """filter_period=2026-10 reflects October metrics and keeps dropdown selected."""
    e1_id = handworked_data["e1_id"]
    res = auth_client.get(f"/employees/{e1_id}/analytics?filter_period=2026-10")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Period title/badge shows Oct 2026 or October 2026
    assert "Oct 2026" in html or "October 2026" in html
    # KPIs: 2 eligible, 100.00% attendance, 0.00% absenteeism
    assert "100.00%" in html
    assert "0.00%" in html
    # Dropdown has 2026-10 selected
    assert 'value="2026-10" selected' in html


def test_analytics_period_filter_september(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """filter_period=2026-09 reflects September metrics and keeps dropdown selected."""
    e1_id = handworked_data["e1_id"]
    res = auth_client.get(f"/employees/{e1_id}/analytics?filter_period=2026-09")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Period title/badge shows Sep 2026 or September 2026
    assert "Sep 2026" in html or "September 2026" in html
    # KPIs: 4 eligible, 75.00% attendance, 25.00% absenteeism
    assert "75.00%" in html
    assert "25.00%" in html
    # Dropdown has 2026-09 selected
    assert 'value="2026-09" selected' in html


def test_analytics_period_filter_all_time_default(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Missing or 'all' filter_period defaults to All Time History (6 eligible, 83.33%)."""
    e1_id = handworked_data["e1_id"]
    for url in [f"/employees/{e1_id}/analytics", f"/employees/{e1_id}/analytics?filter_period=all"]:
        res = auth_client.get(url)
        assert res.status_code == 200
        html = res.data.decode("utf-8")
        assert "All Time History" in html
        assert "83.33%" in html
        assert 'value="all" selected' in html


def test_analytics_period_dropdown_options(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Dropdown lists 'All Time History', 'October 2026' (or Oct 2026), 'September 2026'."""
    e1_id = handworked_data["e1_id"]
    res = auth_client.get(f"/employees/{e1_id}/analytics")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert 'value="all"' in html
    assert "All Time History" in html
    assert 'value="2026-10"' in html
    assert 'value="2026-09"' in html


# =============================================================================
# 2. Department Benchmark dynamically updates with selected period
# =============================================================================

def test_department_benchmark_changes_with_period(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Department benchmark matches 70.00% all-time, 66.67% September, and 75.00% October."""
    e1_id = handworked_data["e1_id"]

    # All time: 70.00% attendance, 30.00% absenteeism
    res_all = auth_client.get(f"/employees/{e1_id}/analytics?filter_period=all")
    html_all = res_all.data.decode("utf-8")
    assert "70.00%" in html_all
    assert "30.00%" in html_all

    # September: 66.67% attendance, 33.33% absenteeism
    res_sep = auth_client.get(f"/employees/{e1_id}/analytics?filter_period=2026-09")
    html_sep = res_sep.data.decode("utf-8")
    assert "66.67%" in html_sep
    assert "33.33%" in html_sep

    # October: 75.00% attendance, 25.00% absenteeism
    res_oct = auth_client.get(f"/employees/{e1_id}/analytics?filter_period=2026-10")
    html_oct = res_oct.data.decode("utf-8")
    assert "75.00%" in html_oct
    assert "25.00%" in html_oct


# =============================================================================
# 3. Bug B: Monthly History Breakdown Table
# =============================================================================

def test_monthly_history_breakdown_values(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Monthly breakdown does NOT show 0/N/A; sums match all-time totals."""
    e1_id = handworked_data["e1_id"]
    res = auth_client.get(f"/employees/{e1_id}/analytics")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Table contains both months
    assert "2026-10" in html
    assert "2026-09" in html

    # October breakdown: 2 present, 0 absent, 100.00%
    assert "100.00%" in html
    # September breakdown: 3 present, 1 absent, 75.00%
    assert "75.00%" in html

    # 'View Month' links must link to filter_period=YYYY-MM
    assert 'filter_period=2026-10' in html
    assert 'filter_period=2026-09' in html


# =============================================================================
# 4. Bug C: Monthly Attendance Trend Chart
# =============================================================================

def test_monthly_attendance_trend_chart_rendered(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Monthly attendance trend chart is generated and does NOT display fallback message."""
    e1_id = handworked_data["e1_id"]
    res = auth_client.get(f"/employees/{e1_id}/analytics")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    assert "No trend data available" not in html
    assert "Monthly Attendance Trend" in html
    # Contains chart image URL
    expected_img_url = f"/charts/file/emp_{e1_id}_trend.png"
    assert expected_img_url in html

    # Verify chart file serves correctly
    chart_res = auth_client.get(expected_img_url)
    assert chart_res.status_code == 200
    assert chart_res.mimetype == "image/png"


# =============================================================================
# 5. Validation and Empty States
# =============================================================================

def test_analytics_invalid_period_returns_400(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Invalid filter_period formats or invalid months return 400 Bad Request."""
    e1_id = handworked_data["e1_id"]
    for bad_period in ["2026-13", "abc", "2026-00", "2026/09", "123"]:
        res = auth_client.get(f"/employees/{e1_id}/analytics?filter_period={bad_period}")
        assert res.status_code == 400, f"Expected 400 for filter_period={bad_period}, got {res.status_code}"


def test_analytics_employee_without_attendance(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Employee with zero attendance records renders without crashing (200 OK)."""
    e3_id = handworked_data["e3_id"]
    res = auth_client.get(f"/employees/{e3_id}/analytics")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "Charlie Brown" in html


def test_report_invalid_query_parameters(auth_client: Any) -> None:
    """Invalid year or month query parameters return 400 Bad Request."""
    bad_urls = [
        "/report?year=2026&month=13",
        "/report?year=abc&month=9",
        "/report?year=2026&month=0",
        "/charts?year=2026&month=13",
        "/charts?year=2026&month=0",
        "/charts?year=xyz&month=9",
    ]
    for url in bad_urls:
        res = auth_client.get(url)
        assert res.status_code == 400, f"Expected 400 for {url}, got {res.status_code}"


# =============================================================================
# 6. Redesigned Report Pages (Modern HTML, KPI cards, No <pre>)
# =============================================================================

def test_redesigned_report_pages_render_and_have_no_pre(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """All 5 report pages render modern tables/cards and do not use <pre> tags."""
    urls = [
        "/summary/employees",
        "/summary/departments",
        "/ranking",
        "/report?year=2026&month=9",
        "/charts?year=2026&month=9",
    ]
    for url in urls:
        res = auth_client.get(url)
        assert res.status_code == 200, f"Failed on {url} with {res.status_code}"
        html = res.data.decode("utf-8")
        assert "<pre" not in html, f"Found <pre> tag in {url}"
        assert ("<table" in html) or ("rpt-card" in html) or ("rpt-chart-card" in html), (
            f"Expected modern markup in {url}"
        )


def test_report_page_september_exact_numbers(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Monthly report for 2026-09 shows accurate departmental attendance (66.67%)."""
    res = auth_client.get("/report?year=2026&month=9")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "66.67%" in html
    assert "33.33%" in html
    assert "Engineering" in html


def test_report_page_empty_month_message(auth_client: Any) -> None:
    """Report for month without attendance records displays exact expected empty message."""
    res = auth_client.get("/report?year=2026&month=8")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "No attendance records for 2026-08." in html
    assert "<pre" not in html


def test_ranking_page_ranks_correctly(auth_client: Any, handworked_data: Dict[str, int]) -> None:
    """Ranking page shows E002 (50.00% absenteeism) ranked above E001 (16.67%)."""
    res = auth_client.get("/ranking")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    pos_e1 = html.find("E001")
    pos_e2 = html.find("E002")
    assert pos_e1 != -1 and pos_e2 != -1
    assert pos_e2 < pos_e1


# =============================================================================
# 7. Unauthenticated Access Protection
# =============================================================================

def test_unauthenticated_access_redirects_to_login(client: Any, handworked_data: Dict[str, int]) -> None:
    """Protected report routes and analytics redirect to /login when unauthenticated."""
    e1_id = handworked_data["e1_id"]
    protected_urls = [
        f"/employees/{e1_id}/analytics",
        "/summary/employees",
        "/summary/departments",
        "/ranking",
        "/report",
        "/charts",
    ]
    for url in protected_urls:
        res = client.get(url)
        assert res.status_code == 302, f"Expected 302 redirect for {url}, got {res.status_code}"
        assert "/login" in res.headers["Location"], f"Expected redirect to /login for {url}"


# =============================================================================
# 8. Architecture, Template & Style Constraints
# =============================================================================

def test_no_safe_filter_or_markup_in_templates() -> None:
    """No template in src/web/templates should contain |safe or Markup."""
    tpl_dir = Path("src/web/templates")
    assert tpl_dir.is_dir()
    for tpl_file in tpl_dir.rglob("*.html"):
        content = tpl_file.read_text(encoding="utf-8")
        assert "|safe" not in content, f"Forbidden '|safe' found in {tpl_file}"
        assert "Markup" not in content, f"Forbidden 'Markup' found in {tpl_file}"


def test_no_sql_keywords_in_src_web() -> None:
    """No python file in src/web may contain SQL query keywords."""
    web_dir = Path("src/web")
    assert web_dir.is_dir()
    sql_pattern = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b")
    for py_file in web_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        matches = sql_pattern.findall(content)
        assert not matches, f"Forbidden SQL keyword {matches} found in {py_file}"


def test_css_naming_conventions() -> None:
    """All custom classes in app.css follow rpt- prefix or standard stat-* card naming."""
    css_path = Path("src/web/static/css/app.css")
    assert css_path.is_file()
    content = css_path.read_text(encoding="utf-8")

    # Extract all top-level class selectors starting with . at line beginning
    if "/* ==========================================================================" in content:
        custom_section = content.split("/* ==========================================================================")[-1]
        selectors = re.findall(r"^\.([a-zA-Z_-][a-zA-Z0-9_-]*)", custom_section, flags=re.MULTILINE)
        allowed_prefixes = ("rpt-", "stat-")
        for sel in selectors:
            assert sel.startswith(allowed_prefixes), f"Class .{sel} does not start with an allowed prefix (rpt-, stat-)"
