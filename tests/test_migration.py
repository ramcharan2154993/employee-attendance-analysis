"""Tests for safe schema migration and recovery."""

import datetime
from src.db import migrate_schema
from src.employees import get_employee


def test_migration_from_old_schema(conn):
    """Simulates an unmigrated database without joining_date and verifies proper backfill."""
    cursor = conn.cursor()
    # Ensure starting clean
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM employees")

    # Drop joining_date to simulate pre-migration legacy schema
    cursor.execute("ALTER TABLE employees DROP COLUMN joining_date")
    conn.commit()

    # Insert legacy employees without joining_date
    cursor.execute(
        """
        INSERT INTO employees (employee_code, employee_name, department, is_active)
        VALUES ('E100', 'Legacy With History', 'Engineering', TRUE),
               ('E101', 'Legacy No History', 'Sales', TRUE)
        """
    )
    conn.commit()

    # Get employee_id for E100
    cursor.execute("SELECT employee_id FROM employees WHERE employee_code = 'E100'")
    e100_id = cursor.fetchone()[0]

    # Add an attendance record for E100 on 2026-08-15
    cursor.execute(
        """
        INSERT INTO attendance (employee_id, attendance_date, status)
        VALUES (%s, '2026-08-15', 'Present'),
               (%s, '2026-08-20', 'Present')
        """,
        (e100_id, e100_id),
    )
    conn.commit()
    cursor.close()

    # Run migration with approved standard fallback date 2026-09-01
    migrate_schema(conn, fallback_date="2026-09-01")

    # Verify column definition
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM employees LIKE 'joining_date'")
    col_info = cur.fetchone()
    cur.close()

    assert col_info is not None
    assert col_info[2] == "NO"  # Nullable == 'NO' (NOT NULL)

    # Verify E100 backfilled with min_date (2026-08-15)
    e100 = get_employee(conn, "E100")
    assert e100 is not None
    assert e100["joining_date"] == datetime.date(2026, 8, 15)

    # Verify E101 backfilled with fallback_date (2026-09-01)
    e101 = get_employee(conn, "E101")
    assert e101 is not None
    assert e101["joining_date"] == datetime.date(2026, 9, 1)


def test_migration_rerun_idempotency(conn):
    """Running migrate_schema multiple times is completely idempotent and preserves data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM employees")
    conn.commit()
    cursor.close()

    # Insert employee with known date
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO employees (employee_code, employee_name, department, is_active, joining_date)
        VALUES ('E102', 'Already Migrated', 'Engineering', TRUE, '2026-05-10')
        """
    )
    conn.commit()
    cur.close()

    # Rerun migration twice
    migrate_schema(conn, fallback_date="2026-09-01")
    migrate_schema(conn, fallback_date="2026-09-01")

    emp = get_employee(conn, "E102")
    assert emp is not None
    assert emp["joining_date"] == datetime.date(2026, 5, 10)


def test_migration_recovery_from_partial_failure(conn):
    """Recovers from partially completed migration (column nullable with NULL rows)."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM employees")
    conn.commit()

    # Simulate partial failure: modify column to NULL and insert NULL row
    cursor.execute("ALTER TABLE employees MODIFY COLUMN joining_date DATE NULL")
    cursor.execute(
        """
        INSERT INTO employees (employee_code, employee_name, department, is_active, joining_date)
        VALUES ('E103', 'Partial Null User', 'Operations', TRUE, NULL)
        """
    )
    conn.commit()
    cursor.close()

    # Run migration
    migrate_schema(conn, fallback_date="2026-09-01")

    # Verify column is NOT NULL again
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM employees LIKE 'joining_date'")
    col_info = cur.fetchone()
    cur.close()
    assert col_info[2] == "NO"

    # Verify NULL row was backfilled with fallback date
    emp = get_employee(conn, "E103")
    assert emp is not None
    assert emp["joining_date"] == datetime.date(2026, 9, 1)
