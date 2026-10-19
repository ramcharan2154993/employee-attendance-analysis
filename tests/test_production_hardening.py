"""Tests for Phase 2 production hardening, security configurations, and rate limiting."""

import os
from typing import Any
import pytest
from flask import Flask
import config
from src.auth import authenticate_user, create_user, get_user_by_username
from src.create_admin import main as create_admin_main
from src.rate_limiter import LoginRateLimiter, login_limiter
from src.web import create_app


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Ensure the global rate limiter is reset before each test."""
    login_limiter.clear()


@pytest.fixture
def test_app() -> Any:
    """Provide a standard test application instance."""
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-unit-testing",
        "DATABASE_NAME": config.DB_TEST_NAME or "attendance_db_test",
        "REQUIRE_AUTH": False,
    })


@pytest.fixture
def client(test_app: Any) -> Any:
    """Provide an unauthenticated client."""
    return test_app.test_client()


@pytest.fixture
def auth_client() -> Any:
    """Provide a client enforcing authentication."""
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-unit-testing",
        "DATABASE_NAME": config.DB_TEST_NAME or "attendance_db_test",
        "REQUIRE_AUTH": True,
    })
    return app.test_client()


def test_production_secret_key_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """In production mode, app must refuse to start if SECRET_KEY is missing, too short, or a placeholder."""
    monkeypatch.setattr(config, "APP_ENV", "production")

    # 1. Missing SECRET_KEY
    monkeypatch.setattr(config, "SECRET_KEY", None)
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_app({"TESTING": False, "SECRET_KEY": None})

    # 2. Too short (< 32 chars)
    short_key = "short-secret-key-12345"
    monkeypatch.setattr(config, "SECRET_KEY", short_key)
    with pytest.raises(RuntimeError, match="minimum length of 32 characters"):
        create_app({"TESTING": False, "SECRET_KEY": short_key})

    # 3. Known placeholder
    placeholder_key = "generate-a-long-random-value"
    monkeypatch.setattr(config, "SECRET_KEY", placeholder_key)
    with pytest.raises(RuntimeError, match="not a placeholder"):
        create_app({"TESTING": False, "SECRET_KEY": placeholder_key})

    # 4. Valid production key (32+ random chars) succeeds
    valid_key = "a" * 32
    monkeypatch.setattr(config, "SECRET_KEY", valid_key)
    app = create_app({"TESTING": False, "SECRET_KEY": valid_key})
    assert isinstance(app, Flask)


def test_development_deprecated_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """In development mode, FLASK_SECRET_KEY triggers deprecation warning if SECRET_KEY unset."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("FLASK_SECRET_KEY", "legacy-dev-secret-key")

    with pytest.deprecated_call():
        resolved = config._resolve_secret_key()
    assert resolved == "legacy-dev-secret-key"


def test_production_secure_cookie_and_hsts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production mode sets SESSION_COOKIE_SECURE=True and adds Strict-Transport-Security header."""
    valid_key = "b" * 32
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "SECRET_KEY", valid_key)

    # In production without TESTING=True
    app = create_app({"TESTING": False, "SECRET_KEY": valid_key})
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    with app.test_client() as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert "Strict-Transport-Security" in resp.headers


def test_development_cookie_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development mode keeps SESSION_COOKIE_SECURE=False for local HTTP use."""
    monkeypatch.setattr(config, "APP_ENV", "development")
    app = create_app({"TESTING": True, "SECRET_KEY": "dev-key", "DATABASE_NAME": "attendance_db_test"})
    assert app.config["SESSION_COOKIE_SECURE"] is False
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_healthz_endpoint(client: Any) -> None:
    """GET /healthz returns 'ok' without authentication or leaking info."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "ok"
    assert resp.content_type == "text/plain; charset=utf-8"


def test_login_rate_limiting_blocks_after_five_attempts(auth_client: Any, conn: Any) -> None:
    """Login throttles after 5 failed attempts and returns HTTP 429."""
    # Create test user
    create_user(conn, "rate_target", "CorrectPassword123!", role="HR")

    with auth_client.session_transaction() as sess:
        sess["csrf_token"] = "token123"

    # 1 to 4: returns 401
    for i in range(4):
        resp = auth_client.post(
            "/login",
            data={"username": "rate_target", "password": "WrongPassword!", "csrf_token": "token123"},
        )
        assert resp.status_code == 401
        assert "Invalid username or password" in resp.get_data(as_text=True)

    # 5th attempt locks the account: returns 429
    resp_5 = auth_client.post(
        "/login",
        data={"username": "rate_target", "password": "WrongPassword!", "csrf_token": "token123"},
    )
    assert resp_5.status_code == 429
    assert "Too many failed login attempts" in resp_5.get_data(as_text=True)

    # 6th attempt with CORRECT password is also rejected because account is locked: returns 429
    resp_6 = auth_client.post(
        "/login",
        data={"username": "rate_target", "password": "CorrectPassword123!", "csrf_token": "token123"},
    )
    assert resp_6.status_code == 429
    assert "Too many failed login attempts" in resp_6.get_data(as_text=True)

    # Reset limiter and test success
    login_limiter.clear()
    resp_success = auth_client.post(
        "/login",
        data={"username": "rate_target", "password": "CorrectPassword123!", "csrf_token": "token123"},
        follow_redirects=True,
    )
    assert resp_success.status_code == 200
    assert "rate_target" in resp_success.get_data(as_text=True)


def test_create_admin_cli(conn: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Interactive create_admin script creates an admin with >=10 char password and checks duplicates."""
    import getpass

    test_db = config.DB_TEST_NAME or "attendance_db_test"

    # 1. Password < 10 chars fails
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "short9")
    ret_short = create_admin_main(["--username", "cli_admin_1", "--database", test_db])
    assert ret_short == 1
    assert "at least 10 characters long" in capsys.readouterr().err

    # 2. Mismatched passwords fail
    pw_sequence = iter(["StrongPassword123!", "MismatchPass456!"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(pw_sequence))
    ret_mismatch = create_admin_main(["--username", "cli_admin_2", "--database", test_db])
    assert ret_mismatch == 1
    assert "Passwords do not match" in capsys.readouterr().err

    # 3. Successful creation
    pw_match = iter(["StrongPassword123!", "StrongPassword123!"])
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(pw_match))
    ret_ok = create_admin_main(["--username", "cli_admin_ok", "--database", test_db])
    assert ret_ok == 0
    assert "created successfully" in capsys.readouterr().out

    user = get_user_by_username(conn, "cli_admin_ok")
    assert user is not None
    assert user["role"] == "Admin"

    # 4. Duplicate username rejected
    ret_dup = create_admin_main(["--username", "cli_admin_ok", "--database", test_db])
    assert ret_dup == 1
    assert "already exists" in capsys.readouterr().err


def test_proxyfix_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """In production with TRUSTED_PROXY_COUNT=1, ProxyFix correctly resolves client IP and proto."""
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")
    valid_key = "c" * 32
    monkeypatch.setattr(config, "SECRET_KEY", valid_key)

    app = create_app({"TESTING": False, "SECRET_KEY": valid_key})
    with app.test_client() as client:
        # Route healthz should see real forwarded IP and HTTPS proto
        resp = client.get(
            "/healthz",
            headers={
                "X-Forwarded-For": "203.0.113.195",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "attendance.example.com",
            },
        )
        assert resp.status_code == 200
        assert resp.get_data(as_text=True) == "ok"


def test_rate_limiting_ip_wide_cap_and_different_ip_isolation(auth_client: Any, conn: Any) -> None:
    """Test that:
    1. Lockout on attacker's IP does not lock out legitimate user from a different IP.
    2. 20 failed attempts from one IP locks that entire IP.
    """
    create_user(conn, "legit_victim", "SecretPass123!", role="HR")

    with auth_client.session_transaction() as sess:
        sess["csrf_token"] = "token_iso"

    # 1. Attacker at 198.51.100.5 fails 5 times trying to guess legit_victim's password
    attacker_ip = "198.51.100.5"
    for _ in range(5):
        resp = auth_client.post(
            "/login",
            environ_base={"REMOTE_ADDR": attacker_ip},
            data={"username": "legit_victim", "password": "WrongPassword!", "csrf_token": "token_iso"},
        )
    assert resp.status_code == 429
    assert "Too many failed login attempts for this account" in resp.get_data(as_text=True)

    # Legitimate user logging in from their home/office IP (192.0.2.1) is NOT locked out!
    legit_ip = "192.0.2.1"
    resp_legit = auth_client.post(
        "/login",
        environ_base={"REMOTE_ADDR": legit_ip},
        data={"username": "legit_victim", "password": "SecretPass123!", "csrf_token": "token_iso"},
        follow_redirects=True,
    )
    assert resp_legit.status_code == 200
    assert "legit_victim" in resp_legit.get_data(as_text=True)

    # 2. An attacker tries dictionary attack with 20 different usernames from single IP 198.51.100.99
    spam_ip = "198.51.100.99"
    with auth_client.session_transaction() as sess:
        sess["csrf_token"] = "token_spam"

    for i in range(19):
        resp_spam = auth_client.post(
            "/login",
            environ_base={"REMOTE_ADDR": spam_ip},
            data={"username": f"random_user_{i}", "password": "WrongPassword!", "csrf_token": "token_spam"},
        )
        assert resp_spam.status_code == 401

    # 20th attempt triggers IP-wide lockout
    resp_20 = auth_client.post(
        "/login",
        environ_base={"REMOTE_ADDR": spam_ip},
        data={"username": "random_user_20", "password": "WrongPassword!", "csrf_token": "token_spam"},
    )
    assert resp_20.status_code == 429
    assert "Too many failed login attempts from your IP address" in resp_20.get_data(as_text=True)
