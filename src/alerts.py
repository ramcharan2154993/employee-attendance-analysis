"""Smart Attendance Warning & Threshold Management Module.

Provides:
- Configurable critical attendance threshold management in system_settings.
- Multi-tier alert classification: Normal (>=85%), Attention (75-85%), Critical (<75%).
- Automated idempotent alert synchronization avoiding duplicate warnings.
- Alert lifecycle tracking (review states, reviewer identity, review notes).
"""

import calendar
import datetime
from typing import Any
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract

from src.analysis import employee_summary, load_attendance_df
from src.calculations import eligible_days


DEFAULT_CRITICAL_THRESHOLD = 75.0


def get_critical_threshold(conn: MySQLConnectionAbstract) -> float:
    """Retrieve the configured critical attendance percentage threshold, defaulting to 75.0."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT setting_value
            FROM system_settings
            WHERE setting_key = 'attendance_critical_threshold'
            """
        )
        row = cursor.fetchone()
        if row and row[0]:
            try:
                return float(row[0])
            except (ValueError, TypeError):
                return DEFAULT_CRITICAL_THRESHOLD
        return DEFAULT_CRITICAL_THRESHOLD
    finally:
        cursor.close()


def set_critical_threshold(
    conn: MySQLConnectionAbstract,
    threshold: float,
) -> float:
    """Update the critical attendance percentage threshold (0.0 to 100.0)."""
    if threshold < 0.0 or threshold > 100.0:
        raise ValueError(f"Threshold must be between 0.0% and 100.0%, got: {threshold}%.")

    rounded_threshold = round(threshold, 2)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value, description)
            VALUES ('attendance_critical_threshold', %s, 'Critical attendance warning threshold percentage')
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            (str(rounded_threshold),),
        )
        conn.commit()
        return rounded_threshold
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def classify_attendance_level(
    attendance_pct: float | None,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
    threshold: float | None = None,
) -> tuple[str, str]:
    """Classify attendance into compliance warning tiers.

    Returns:
        (level_code, human_label)
        Level codes: 'CRITICAL', 'ATTENTION', 'NORMAL', 'NO_DATA'
    """
    if threshold is not None:
        critical_threshold = threshold

    if attendance_pct is None:
        return "NO_DATA", "No Records"
    if attendance_pct < critical_threshold:
        return "CRITICAL", f"Critical (< {critical_threshold:.0f}%)"
    if attendance_pct < 85.0:
        return "ATTENTION", "Attention (75% - 85%)"
    return "NORMAL", "Normal (>= 85%)"


def sync_monthly_attendance_alerts(
    conn: MySQLConnectionAbstract,
    year: int,
    month: int,
    critical_threshold: float | None = None,
) -> int:
    """Idempotently compute and record warnings for employees under 85% attendance for a given month."""
    if critical_threshold is None:
        critical_threshold = get_critical_threshold(conn)

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    if df.empty:
        return 0

    emp_summary_df = employee_summary(df)
    if emp_summary_df.empty:
        return 0

    # Retrieve employee code to ID mapping
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT employee_code, employee_id FROM employees")
        code_to_id = {c: emp_id for c, emp_id in cursor.fetchall()}

        synced_count = 0
        for _, row in emp_summary_df.iterrows():
            code = row["employee_code"]
            emp_id = code_to_id.get(code)
            if not emp_id:
                continue

            att_pct = row["attendance_pct"]
            if att_pct is None:
                continue

            level, _ = classify_attendance_level(att_pct, critical_threshold)
            # Only record alerts for CRITICAL or ATTENTION
            if level not in ("CRITICAL", "ATTENTION"):
                continue

            cursor.execute(
                """
                INSERT INTO attendance_alerts (
                    employee_id, year, month, attendance_pct, eligible_days,
                    present_days, absent_days, warning_level, threshold_applied
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    attendance_pct = VALUES(attendance_pct),
                    eligible_days = VALUES(eligible_days),
                    present_days = VALUES(present_days),
                    absent_days = VALUES(absent_days),
                    warning_level = VALUES(warning_level),
                    threshold_applied = VALUES(threshold_applied)
                """,
                (
                    emp_id,
                    year,
                    month,
                    round(att_pct, 2),
                    int(row["eligible_days"]),
                    int(row["present"]),
                    int(row["absent"]),
                    level,
                    critical_threshold,
                ),
            )
            synced_count += 1

        conn.commit()
        return synced_count
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def list_attendance_alerts(
    conn: MySQLConnectionAbstract,
    year: int | None = None,
    month: int | None = None,
    department: str | None = None,
    warning_level: str | None = None,
    is_reviewed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve historical and active alerts with employee and reviewer metadata."""
    cursor = conn.cursor(dictionary=True)
    try:
        dept_val = department.strip() if department and department.strip() and department.strip().lower() != "all" else None
        level_val = warning_level.strip().upper() if warning_level and warning_level.strip() and warning_level.strip().lower() != "all" else None

        sql = """
            SELECT
                a.alert_id,
                a.employee_id,
                a.year,
                a.month,
                a.attendance_pct,
                a.eligible_days,
                a.present_days,
                a.absent_days,
                a.warning_level,
                a.threshold_applied,
                a.is_reviewed,
                a.reviewed_by,
                a.reviewed_at,
                a.notes,
                a.created_at,
                e.employee_code,
                e.employee_name,
                e.department,
                e.email,
                e.mobile_number,
                u.username AS reviewer_username
            FROM attendance_alerts a
            JOIN employees e ON a.employee_id = e.employee_id
            LEFT JOIN users u ON a.reviewed_by = u.user_id
            WHERE (%s IS NULL OR a.year = %s)
              AND (%s IS NULL OR a.month = %s)
              AND (%s IS NULL OR e.department = %s)
              AND (%s IS NULL OR a.warning_level = %s)
              AND (%s IS NULL OR a.is_reviewed = %s)
            ORDER BY
                CASE a.warning_level
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'ATTENTION' THEN 2
                    ELSE 3
                END ASC,
                a.is_reviewed ASC,
                a.attendance_pct ASC,
                a.created_at DESC
            LIMIT %s OFFSET %s
        """
        params = [
            year, year,
            month, month,
            dept_val, dept_val,
            level_val, level_val,
            is_reviewed, is_reviewed,
            int(limit), int(offset),
        ]
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            r["is_reviewed"] = bool(r["is_reviewed"])
            r["period_label"] = datetime.date(r["year"], r["month"], 1).strftime("%B %Y")
        return rows
    finally:
        cursor.close()


def count_attendance_alerts(
    conn: MySQLConnectionAbstract,
    year: int | None = None,
    month: int | None = None,
    department: str | None = None,
    warning_level: str | None = None,
    is_reviewed: bool | None = None,
) -> int:
    """Return count of alerts matching given filters for pagination badges."""
    cursor = conn.cursor()
    try:
        dept_val = department.strip() if department and department.strip() and department.strip().lower() != "all" else None
        level_val = warning_level.strip().upper() if warning_level and warning_level.strip() and warning_level.strip().lower() != "all" else None

        sql = """
            SELECT COUNT(*)
            FROM attendance_alerts a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE (%s IS NULL OR a.year = %s)
              AND (%s IS NULL OR a.month = %s)
              AND (%s IS NULL OR e.department = %s)
              AND (%s IS NULL OR a.warning_level = %s)
              AND (%s IS NULL OR a.is_reviewed = %s)
        """
        params = [
            year, year,
            month, month,
            dept_val, dept_val,
            level_val, level_val,
            is_reviewed, is_reviewed,
        ]
        cursor.execute(sql, tuple(params))
        (total,) = cursor.fetchone()
        return total
    finally:
        cursor.close()


def mark_alert_reviewed(
    conn: MySQLConnectionAbstract,
    alert_id: int,
    user_id: int | None = None,
    notes: str | None = None,
) -> None:
    """Mark an attendance warning as reviewed by an HR/Admin user."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE attendance_alerts
            SET is_reviewed = TRUE,
                reviewed_by = %s,
                reviewed_at = NOW(),
                notes = COALESCE(%s, notes)
            WHERE alert_id = %s
            """,
            (user_id, notes.strip() if notes and notes.strip() else None, alert_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Alert with ID {alert_id} not found.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_alert_metrics_summary(
    conn: MySQLConnectionAbstract,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, int]:
    """Return high-level summary counters: critical, attention, and unreviewed counts."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN warning_level = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_cnt,
                SUM(CASE WHEN warning_level = 'ATTENTION' THEN 1 ELSE 0 END) AS attention_cnt,
                SUM(CASE WHEN is_reviewed = FALSE THEN 1 ELSE 0 END) AS unreviewed_cnt,
                COUNT(*) AS total_cnt
            FROM attendance_alerts
            WHERE (%s IS NULL OR year = %s)
              AND (%s IS NULL OR month = %s)
            """,
            (year, year, month, month),
        )
        row = cursor.fetchone()
        if not row or row[3] == 0:
            return {"critical": 0, "attention": 0, "unreviewed": 0, "total": 0}
        return {
            "critical": int(row[0] or 0),
            "attention": int(row[1] or 0),
            "unreviewed": int(row[2] or 0),
            "total": int(row[3] or 0),
        }
    finally:
        cursor.close()
