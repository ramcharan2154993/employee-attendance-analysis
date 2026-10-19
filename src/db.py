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


def migrate_schema(
    conn: MySQLConnectionAbstract,
    fallback_date: str = "2026-09-01",
) -> None:
    """Safely and idempotently migrate database schema to ensure joining_date exists.

    1. Detects whether joining_date column already exists in employees table.
    2. If missing, adds it as nullable.
    3. Backfills existing records with earliest attendance date, or fallback_date.
    4. Confirms no NULL values remain.
    5. Modifies column to NOT NULL.
    6. Safe to rerun and recovers from partially completed migrations without data loss.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'employees'")
        if not cursor.fetchone():
            return

        cursor.execute("SHOW COLUMNS FROM employees LIKE 'joining_date'")
        col_info = cursor.fetchone()

        if col_info is None:
            cursor.execute("ALTER TABLE employees ADD COLUMN joining_date DATE NULL")
            conn.commit()
            cursor.execute("SHOW COLUMNS FROM employees LIKE 'joining_date'")
            col_info = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) FROM employees WHERE joining_date IS NULL")
        (null_count,) = cursor.fetchone()
        if null_count > 0:
            cursor.execute(
                """
                UPDATE employees e
                LEFT JOIN (
                    SELECT employee_id, MIN(attendance_date) AS min_date
                    FROM attendance
                    GROUP BY employee_id
                ) a ON e.employee_id = a.employee_id
                SET e.joining_date = COALESCE(a.min_date, %s)
                WHERE e.joining_date IS NULL
                """,
                (fallback_date,),
            )
            conn.commit()

        cursor.execute("SELECT COUNT(*) FROM employees WHERE joining_date IS NULL")
        (remaining_nulls,) = cursor.fetchone()
        if remaining_nulls > 0:
            raise RuntimeError(
                f"Migration failed: {remaining_nulls} employees still have NULL joining_date."
            )

        if col_info and col_info[2] == "YES":
            cursor.execute(
                "ALTER TABLE employees MODIFY COLUMN joining_date DATE NOT NULL"
            )
            conn.commit()
    finally:
        cursor.close()


def apply_schema(database_name: str) -> None:
    """Read database/schema.sql, apply each statement, and execute schema migrations."""
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
        migrate_schema(conn)
    finally:
        conn.close()

