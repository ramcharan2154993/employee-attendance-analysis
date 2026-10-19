"""Audit trail logging and querying for attendance operations."""

import datetime
from typing import Any
from mysql.connector.abstracts import MySQLConnectionAbstract


def log_attendance_action(
    conn: MySQLConnectionAbstract,
    employee_id: int,
    attendance_date: datetime.date,
    action_type: str,
    new_status: str,
    previous_status: str | None = None,
    attendance_id: int | None = None,
    reason: str | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> int:
    """Append-only logging of attendance creation and correction events."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO attendance_audit (
                attendance_id,
                employee_id,
                attendance_date,
                action_type,
                previous_status,
                new_status,
                correction_reason,
                user_id,
                username
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                attendance_id,
                employee_id,
                attendance_date,
                action_type,
                previous_status,
                new_status,
                reason.strip() if reason and reason.strip() else None,
                user_id,
                username.strip() if username and username.strip() else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_audit_trail(
    conn: MySQLConnectionAbstract,
    employee_id: int | None = None,
    action_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve immutable audit history records with employee context ordered by time descending."""
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                a.audit_id,
                a.attendance_id,
                a.employee_id,
                e.employee_code,
                e.employee_name,
                e.department,
                a.attendance_date,
                a.action_type,
                a.previous_status,
                a.new_status,
                a.correction_reason,
                a.user_id,
                a.username,
                a.created_at
            FROM attendance_audit a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE (%s IS NULL OR a.employee_id = %s)
              AND (%s IS NULL OR a.action_type = %s)
            ORDER BY a.audit_id DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(
            query,
            (employee_id, employee_id, action_type, action_type, limit, offset),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def count_audit_records(
    conn: MySQLConnectionAbstract,
    employee_id: int | None = None,
    action_type: str | None = None,
) -> int:
    """Return total count of audit records matching optional filters."""
    cursor = conn.cursor()
    try:
        query = """
            SELECT COUNT(*)
            FROM attendance_audit
            WHERE (%s IS NULL OR employee_id = %s)
              AND (%s IS NULL OR action_type = %s)
        """
        cursor.execute(query, (employee_id, employee_id, action_type, action_type))
        (count,) = cursor.fetchone()
        return count
    finally:
        cursor.close()
