"""Unit and integration tests for the public landing page (/welcome).

Covers Decision D8:
- GET /welcome is accessible publicly without authentication.
- Auth is still enforced on all other application endpoints.
- Landing page contains no real employee data or database contents.
- Dynamic CTA adapts when authenticated ("Open dashboard" vs "Sign in").
- Strict CSP security headers and no external or inline scripts.
- Login page links back to /welcome.
"""
from pathlib import Path
from typing import Any
import pytest
import config
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
    """Provide a test client with strict auth enforcement enabled."""
    return test_app.test_client()


def test_unauthenticated_welcome_returns_200(auth_client: Any) -> None:
    """1. Unauthenticated GET /welcome returns 200 with auth enforced."""
    res = auth_client.get("/welcome")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "<!DOCTYPE html>" in html


def test_welcome_page_content_structure(auth_client: Any) -> None:
    """2. Page contains the app name, a link to /login, and the h1 text."""
    res = auth_client.get("/welcome")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # App name and tagline
    assert config.APP_NAME in html
    assert "/login" in html

    # Exactly one <h1> with the expected text
    assert html.count("<h1") == 1
    assert "Attendance intelligence for modern teams" in html

    # Main sections and headings
    assert "Features" in html
    assert "How it works" in html
    assert "Rules you can trust" in html
    assert "Attendance % = Present ÷ (Present + Absent + Leave) × 100" in html


def test_welcome_page_has_no_seeded_employee_data(auth_client: Any) -> None:
    """3. Page contains no seeded employee names (e.g. Asha Rao, Ravi Kumar, Meera Nair) and no E001."""
    res = auth_client.get("/welcome")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Must contain zero real/seeded employee names or codes
    forbidden_names = [
        "Asha Rao",
        "Asha Sharma",
        "Ravi Kumar",
        "Meera Nair",
        "Kiran Patel",
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
    ]
    for forbidden in forbidden_names:
        assert forbidden not in html, f"Found seeded data '{forbidden}' in public landing page"

    # Must contain explicit 'Sample data' label and required sample numbers
    assert "Sample data" in html
    assert "85.71%" in html
    assert "9.52%" in html
    assert "6 employees" in html


def test_other_endpoints_still_require_auth(auth_client: Any) -> None:
    """4. Unauthenticated GET / returns 302 to /login. GET /employees redirects. POST /attendance/new returns 401."""
    # GET / redirects to /login
    res_root = auth_client.get("/")
    assert res_root.status_code == 302
    assert "/login" in res_root.headers.get("Location", "")

    # GET /employees redirects to /login
    res_emp = auth_client.get("/employees")
    assert res_emp.status_code == 302
    assert "/login" in res_emp.headers.get("Location", "")

    # POST /attendance/new returns 401 Unauthorized
    res_post = auth_client.post("/attendance/new", data={"employee_code": "E001"})
    assert res_post.status_code == 401


def test_authenticated_welcome_shows_open_dashboard(auth_client: Any) -> None:
    """5. Authenticated GET /welcome shows 'Open dashboard' and not 'Sign in'."""
    # When unauthenticated:
    res_unauth = auth_client.get("/welcome")
    html_unauth = res_unauth.get_data(as_text=True)
    assert "Sign in" in html_unauth
    assert "Open dashboard" not in html_unauth

    # Log in user via session transaction
    with auth_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "test_admin"
        sess["role"] = "Admin"

    # When authenticated:
    res_auth = auth_client.get("/welcome")
    assert res_auth.status_code == 200
    html_auth = res_auth.get_data(as_text=True)
    assert "Open dashboard" in html_auth
    assert "Sign in" not in html_auth


def test_welcome_security_headers_and_no_external_resources(auth_client: Any) -> None:
    """6. Response headers include CSP; HTML contains no <script tag and no http:// or https:// URLs."""
    res = auth_client.get("/welcome")
    assert res.status_code == 200

    # Content-Security-Policy header
    csp = res.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp

    html = res.get_data(as_text=True)

    # Strictly no <script tags
    assert "<script" not in html.lower()

    # Strictly no external resource URLs (http:// or https://)
    assert "http://" not in html
    assert "https://" not in html


def test_login_page_has_back_to_home_link(auth_client: Any) -> None:
    """7. login.html contains the link back to /welcome."""
    res = auth_client.get("/login")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'href="/welcome"' in html
    assert "Back to home" in html

