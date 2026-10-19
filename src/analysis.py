"""Attendance analysis and aggregation using Pandas and NumPy."""

import datetime
from typing import Any
import pandas as pd
from mysql.connector.abstracts import MySQLConnectionAbstract
from src.calculations import calculate_percentages

ATTENDANCE_DF_COLS = [
    "employee_code",
    "employee_name",
    "department",
    "is_active",
    "joining_date",
    "attendance_date",
    "status",
]

EMPLOYEE_SUMMARY_COLS = [
    "employee_code",
    "employee_name",
    "department",
    "present",
    "absent",
    "leave",
    "holiday",
    "eligible_days",
    "attendance_pct",
    "absenteeism_pct",
]

DEPARTMENT_SUMMARY_COLS = [
    "department",
    "present",
    "absent",
    "leave",
    "holiday",
    "eligible_days",
    "attendance_pct",
    "absenteeism_pct",
]

MONTHLY_SUMMARY_COLS = [
    "month",
    "present",
    "absent",
    "leave",
    "holiday",
    "eligible_days",
    "attendance_pct",
    "absenteeism_pct",
]

RANKING_COLS = [
    "employee_code",
    "employee_name",
    "department",
    "absent",
    "eligible_days",
    "absenteeism_pct",
]


def load_attendance_df(
    conn: MySQLConnectionAbstract,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> pd.DataFrame:
    """Load attendance joined with employees into a Pandas DataFrame using a cursor."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    cursor = conn.cursor()
    try:
        query = """
            SELECT
                e.employee_code,
                e.employee_name,
                e.department,
                e.is_active,
                e.joining_date,
                a.attendance_date,
                a.status
            FROM employees e
            LEFT JOIN attendance a ON e.employee_id = a.employee_id
                AND (%s IS NULL OR a.attendance_date >= %s)
                AND (%s IS NULL OR a.attendance_date <= %s)
            WHERE (%s IS NULL OR e.joining_date <= %s)
            ORDER BY e.employee_code, a.attendance_date
        """
        cursor.execute(
            query,
            (start_date, start_date, end_date, end_date, end_date, end_date),
        )
        rows = cursor.fetchall()
        if not rows:
            return pd.DataFrame(columns=ATTENDANCE_DF_COLS)

        df = pd.DataFrame(rows, columns=ATTENDANCE_DF_COLS)
        df["is_active"] = df["is_active"].astype(bool)
        return df
    finally:
        cursor.close()


def employee_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate attendance counts and calculate percentages per employee."""
    if df.empty or "employee_code" not in df.columns:
        return pd.DataFrame(columns=EMPLOYEE_SUMMARY_COLS)

    records = []
    grouped = df.groupby(
        ["employee_code", "employee_name", "department"],
        sort=True,
        dropna=False,
    )
    for (code, name, dept), group in grouped:
        present = int((group["status"] == "Present").sum())
        absent = int((group["status"] == "Absent").sum())
        leave = int((group["status"] == "Leave").sum())
        holiday = int((group["status"] == "Holiday").sum())
        eligible = present + absent + leave
        records.append({
            "employee_code": code,
            "employee_name": name,
            "department": dept,
            "present": present,
            "absent": absent,
            "leave": leave,
            "holiday": holiday,
            "eligible_days": eligible,
        })

    res = pd.DataFrame(records)
    if res.empty:
        return pd.DataFrame(columns=EMPLOYEE_SUMMARY_COLS)

    res["attendance_pct"] = calculate_percentages(
        res["present"].values, res["eligible_days"].values
    )
    res["absenteeism_pct"] = calculate_percentages(
        res["absent"].values, res["eligible_days"].values
    )
    return res[EMPLOYEE_SUMMARY_COLS].sort_values("employee_code").reset_index(drop=True)


def department_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate attendance counts and calculate percentages per department."""
    if df.empty or "department" not in df.columns:
        return pd.DataFrame(columns=DEPARTMENT_SUMMARY_COLS)

    records = []
    grouped = df.groupby("department", sort=True, dropna=False)
    for dept, group in grouped:
        present = int((group["status"] == "Present").sum())
        absent = int((group["status"] == "Absent").sum())
        leave = int((group["status"] == "Leave").sum())
        holiday = int((group["status"] == "Holiday").sum())
        eligible = present + absent + leave
        records.append({
            "department": dept,
            "present": present,
            "absent": absent,
            "leave": leave,
            "holiday": holiday,
            "eligible_days": eligible,
        })

    res = pd.DataFrame(records)
    if res.empty:
        return pd.DataFrame(columns=DEPARTMENT_SUMMARY_COLS)

    res["attendance_pct"] = calculate_percentages(
        res["present"].values, res["eligible_days"].values
    )
    res["absenteeism_pct"] = calculate_percentages(
        res["absent"].values, res["eligible_days"].values
    )
    return res[DEPARTMENT_SUMMARY_COLS].sort_values("department").reset_index(drop=True)


def _format_month(val: Any) -> str | None:
    """Helper to format a date-like object into 'YYYY-MM' format."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.date, datetime.datetime, pd.Timestamp)):
        return val.strftime("%Y-%m")
    s = str(val).strip()
    return s[:7] if len(s) >= 7 else None


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate attendance counts and calculate percentages per month."""
    if df.empty or "attendance_date" not in df.columns:
        return pd.DataFrame(columns=MONTHLY_SUMMARY_COLS)

    valid_dates_df = df[df["attendance_date"].notna()].copy()
    if valid_dates_df.empty:
        return pd.DataFrame(columns=MONTHLY_SUMMARY_COLS)

    valid_dates_df["month"] = valid_dates_df["attendance_date"].apply(_format_month)
    valid_dates_df = valid_dates_df[valid_dates_df["month"].notna()]
    if valid_dates_df.empty:
        return pd.DataFrame(columns=MONTHLY_SUMMARY_COLS)

    records = []
    grouped = valid_dates_df.groupby("month", sort=True)
    for month_val, group in grouped:
        present = int((group["status"] == "Present").sum())
        absent = int((group["status"] == "Absent").sum())
        leave = int((group["status"] == "Leave").sum())
        holiday = int((group["status"] == "Holiday").sum())
        eligible = present + absent + leave
        records.append({
            "month": month_val,
            "present": present,
            "absent": absent,
            "leave": leave,
            "holiday": holiday,
            "eligible_days": eligible,
        })

    res = pd.DataFrame(records)
    if res.empty:
        return pd.DataFrame(columns=MONTHLY_SUMMARY_COLS)

    res["attendance_pct"] = calculate_percentages(
        res["present"].values, res["eligible_days"].values
    )
    res["absenteeism_pct"] = calculate_percentages(
        res["absent"].values, res["eligible_days"].values
    )
    return res[MONTHLY_SUMMARY_COLS].sort_values("month").reset_index(drop=True)


def absenteeism_ranking(employee_summary_df: pd.DataFrame) -> pd.DataFrame:
    """Rank employees by absenteeism percentage descending, with NaN last and code ties ascending."""
    if employee_summary_df.empty or "absenteeism_pct" not in employee_summary_df.columns:
        return pd.DataFrame(columns=RANKING_COLS)

    res = employee_summary_df[RANKING_COLS].copy()
    res = res.sort_values(
        by=["absenteeism_pct", "employee_code"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)
    return res


def get_dashboard_summary(
    conn: MySQLConnectionAbstract,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Calculate organization-wide KPI metrics for the given or latest month."""
    if year is None or month is None:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(attendance_date) FROM attendance")
            row = cursor.fetchone()
            if row and row[0]:
                max_date = row[0]
                if isinstance(max_date, str):
                    max_date = datetime.date.fromisoformat(max_date)
                year = max_date.year
                month = max_date.month
            else:
                year = 2026
                month = 9
        finally:
            cursor.close()

    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    if df.empty:
        return {
            "year": year,
            "month": month,
            "month_name": start_date.strftime("%B %Y"),
            "present": 0,
            "absent": 0,
            "leave": 0,
            "holiday": 0,
            "eligible_days": 0,
            "attendance_pct": None,
            "absenteeism_pct": None,
        }

    present = int((df["status"] == "Present").sum())
    absent = int((df["status"] == "Absent").sum())
    leave = int((df["status"] == "Leave").sum())
    holiday = int((df["status"] == "Holiday").sum())
    eligible = present + absent + leave

    from src.calculations import (
        calculate_absenteeism_percentage,
        calculate_attendance_percentage,
    )

    att_pct = calculate_attendance_percentage(present, absent, leave)
    abs_pct = calculate_absenteeism_percentage(present, absent, leave)

    return {
        "year": year,
        "month": month,
        "month_name": start_date.strftime("%B %Y"),
        "present": present,
        "absent": absent,
        "leave": leave,
        "holiday": holiday,
        "eligible_days": eligible,
        "attendance_pct": att_pct,
        "absenteeism_pct": abs_pct,
    }

