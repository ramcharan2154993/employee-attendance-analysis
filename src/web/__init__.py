"""Flask application factory and configuration for Employee Attendance Analysis System."""

from typing import Any
from flask import Flask, current_app, g, render_template
import mysql.connector
import config
from src.db import get_connection, require_test_database


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the Flask web application."""
    app = Flask(__name__)
    app.debug = False

    app.config.from_mapping(
        SECRET_KEY=config.FLASK_SECRET_KEY,
        DATABASE_NAME=None,
        OUTPUT_DIR="output",
        TESTING=False,
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
        raise RuntimeError("FLASK_SECRET_KEY is not set in .env")

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
            "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'"
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

    from src.web.routes import bp

    app.register_blueprint(bp)

    return app


def get_db() -> Any:
    """Obtain or reuse the per-request database connection stored in flask.g."""
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE_NAME"])
    return g.db


def run() -> None:
    """Run the Flask web server on local interface."""
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
