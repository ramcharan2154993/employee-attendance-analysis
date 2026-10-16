"""Database connection and schema management utilities."""

from pathlib import Path
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
import config


def get_connection(
    database_name: str | None = None,
) -> MySQLConnectionAbstract:
    """Establish and return a MySQL database connection using config settings.

    If database_name is None, config.DB_NAME is used.
    """
    target_db = database_name if database_name is not None else config.DB_NAME
    try:
        connection = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=target_db,
        )
        return connection
    except Exception as exc:
        err_msg = str(exc)
        if config.DB_PASSWORD and config.DB_PASSWORD in err_msg:
            err_msg = err_msg.replace(config.DB_PASSWORD, "******")
        raise ConnectionError(
            f"Failed to connect to MySQL database: {err_msg}"
        ) from None


def require_test_database(database_name: str) -> None:
    """Verify that the database name ends with '_test' to protect production data."""
    if not database_name.endswith("_test"):
        raise ValueError(
            f"Operation rejected: Database '{database_name}' must end with '_test' for tests."
        )


def apply_schema(database_name: str) -> None:
    """Read database/schema.sql and apply each SQL statement to the specified database."""
    schema_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    conn = get_connection(database_name)
    try:
        cursor = conn.cursor()
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
        cursor.close()
    finally:
        conn.close()
