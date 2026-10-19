from functools import wraps
import hmac
import os
import secrets
from typing import Any
from flask import Flask, current_app, g, redirect, render_template, request, session, url_for
import mysql.connector
import config
from src.db import get_connection, require_test_database


def role_required(*allowed_roles: str):
    """Decorator to enforce role-based access control on routes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            user = g.get("current_user")
            if not user:
                return redirect(url_for("routes.login", next=request.path))
            if allowed_roles and user.get("role") not in allowed_roles:
                return (
                    render_template(
                        "error.html",
                        message="Forbidden: You do not have permission to access this resource.",
                    ),
                    403,
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_required(f):
    """Decorator requiring an authenticated user."""
    return role_required()(f)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask web application."""
    app = Flask(__name__)

    # Debug is strictly OFF by default; only allowed when FLASK_DEBUG=1 in local development
    flask_debug = os.getenv("FLASK_DEBUG", "0") == "1"
    if config.APP_ENV == "production":
        flask_debug = False
    app.debug = flask_debug

    is_production = (config.APP_ENV == "production") and not (test_config and test_config.get("TESTING"))

    app.config.from_mapping(
        SECRET_KEY=config.SECRET_KEY,
        DATABASE_NAME=None,
        OUTPUT_DIR="output",
        TESTING=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_production,
    )

    if test_config:
        app.config.update(test_config)

    if app.config.get("TESTING"):
        db_name = app.config.get("DATABASE_NAME")
        if not db_name or not isinstance(db_name, str):
            raise ValueError(
                f"Test database name must be a valid string, got: {db_name}"
            )
        require_test_database(db_name)

    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY is not set in environment or config.")

    # In production, refuse to start if SECRET_KEY is missing, too short, or a placeholder
    if config.APP_ENV == "production" and not app.config.get("TESTING"):
        placeholders = {
            "generate-a-long-random-value",
            "change_me",
            "placeholder",
            "your_secret_key",
            "secret",
            "secret_key",
        }
        if secret_key.lower().strip() in placeholders or "change_me" in secret_key.lower():
            raise RuntimeError(
                "Production mode requires a real, cryptographically random SECRET_KEY, not a placeholder."
            )
        if len(secret_key) < 32:
            raise RuntimeError(
                "Production mode requires a SECRET_KEY with minimum length of 32 characters."
            )

    @app.teardown_appcontext
    def teardown_db(exception: Any = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.after_request
    def set_security_headers(response: Any) -> Any:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'"
        )
        if config.APP_ENV == "production" and not app.config.get("TESTING"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(404)
    def not_found_error(error: Any) -> tuple[str, int]:
        return render_template("error.html", message="Page not found"), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error: Any) -> tuple[str, int]:
        return render_template("error.html", message="Method not allowed"), 405

    @app.errorhandler(500)
    def internal_error(error: Any) -> tuple[str, int]:
        app.logger.exception("Internal server error: %s", error)
        return (
            render_template(
                "error.html",
                message="Database or server error. See the server console.",
            ),
            500,
        )

    @app.errorhandler(mysql.connector.Error)
    def db_error(error: mysql.connector.Error) -> tuple[str, int]:
        app.logger.exception("Database error occurred: %s", error)
        return (
            render_template(
                "error.html",
                message="Database or server error. See the server console.",
            ),
            500,
        )

    @app.errorhandler(ValueError)
    def value_error(error: ValueError) -> tuple[str, int]:
        return render_template("error.html", message=f"Error: {error}"), 400

    @app.context_processor
    def inject_template_globals() -> dict[str, Any]:
        def csrf_token() -> str:
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_hex(16)
            return session["csrf_token"]

        return {
            "csrf_token": csrf_token,
            "current_user": g.get("current_user"),
            "APP_NAME": config.APP_NAME,
            "APP_TAGLINE": config.APP_TAGLINE,
        }

    @app.before_request
    def load_user_and_authenticate() -> Any:
        user_id = session.get("user_id")
        if user_id:
            g.current_user = {
                "user_id": user_id,
                "username": session.get("username"),
                "role": session.get("role", "HR"),
            }
        else:
            g.current_user = None

        require_auth = app.config.get(
            "REQUIRE_AUTH", not app.config.get("TESTING", False)
        )
        if not require_auth and g.current_user is None:
            g.current_user = {
                "user_id": 1,
                "username": "admin",
                "role": "Admin",
            }

        if require_auth and g.current_user is None:
            endpoint = request.endpoint
            exempt = {"routes.login", "static", "routes.healthz"}
            if endpoint and endpoint not in exempt:
                if request.method == "GET":
                    target = request.full_path if request.query_string else request.path
                    return redirect(url_for("routes.login", next=target))
                return (
                    render_template(
                        "error.html",
                        message="Unauthorized: Please sign in to continue.",
                    ),
                    401,
                )

        if request.method == "POST":
            if request.url_rule is None:
                return None
            token_form = request.form.get("csrf_token")
            token_session = session.get("csrf_token")
            if (
                not token_form
                or not token_session
                or not hmac.compare_digest(token_form, token_session)
            ):
                return (
                    render_template(
                        "error.html",
                        message="Error: invalid or missing form token.",
                    ),
                    400,
                )
        return None

    from src.web.routes import bp
    from src.web.write_routes import write_bp

    app.register_blueprint(bp)
    app.register_blueprint(write_bp)

    # Configure ProxyFix for reverse proxies (PythonAnywhere, Nginx, Render)
    default_proxy_count = 1 if config.APP_ENV == "production" else 0
    try:
        trusted_proxies = int(os.getenv("TRUSTED_PROXY_COUNT", str(default_proxy_count)))
    except (ValueError, TypeError):
        trusted_proxies = default_proxy_count

    if trusted_proxies > 0 and not app.config.get("TESTING"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_proxies,
            x_proto=trusted_proxies,
            x_host=trusted_proxies,
            x_port=trusted_proxies,
            x_prefix=trusted_proxies,
        )

    return app


def get_db() -> Any:
    """Obtain or reuse the per-request database connection stored in flask.g."""
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_NAME"])
    return g.db


def run() -> None:
    """Run the Flask web server on local interface."""
    app = create_app()
    with app.app_context():
        try:
            from src.db import apply_schema
            apply_schema(config.DB_NAME)
        except Exception as e:
            app.logger.warning("Schema check skipped: %s", e)
    app.run(host="127.0.0.1", port=5000, debug=False)

