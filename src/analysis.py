"""Attendance analysis and aggregation using Pandas and NumPy."""

import calendar
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


def get_available_months(
    conn: MySQLConnectionAbstract,
) -> list[tuple[int, int, str]]:
    """Return a list of (year, month, formatted_label) for all months with attendance records, ordered descending."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT DISTINCT YEAR(attendance_date), MONTH(attendance_date)
            FROM attendance
            WHERE attendance_date IS NOT NULL
            ORDER BY YEAR(attendance_date) DESC, MONTH(attendance_date) DESC
            """
        )
        rows = cursor.fetchall()
        if not rows:
            return [(2026, 9, "September 2026")]
        result = []
        for y, m in rows:
            dt = datetime.date(y, m, 1)
            result.append((y, m, dt.strftime("%B %Y")))
        return result
    finally:
        cursor.close()


def get_employee_analytics_data(
    conn: MySQLConnectionAbstract,
    employee_id: int,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Retrieve database-backed attendance analytics for an individual employee."""
    import calendar
    from src.calculations import (
        calculate_absenteeism_percentage,
        calculate_attendance_percentage,
        eligible_days,
    )

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date,
                   email, mobile_number, alt_phone, designation, profile_photo
            FROM employees
            WHERE employee_id = %s
            """,
            (employee_id,),
        )
        emp = cursor.fetchone()
        if not emp:
            raise ValueError(f"Employee with ID {employee_id} not found.")

        start_date = None
        end_date = None
        reporting_period_label = "All Time"
        if year is not None and month is not None:
            _, last_day = calendar.monthrange(year, month)
            start_date = datetime.date(year, month, 1)
            end_date = datetime.date(year, month, last_day)
            reporting_period_label = start_date.strftime("%B %Y")

        cursor.execute(
            """
            SELECT attendance_id, attendance_date, status
            FROM attendance
            WHERE employee_id = %s
            ORDER BY attendance_date DESC
            """,
            (employee_id,),
        )
        all_records = cursor.fetchall()

        period_records = []
        for r in all_records:
            ad = r["attendance_date"]
            if isinstance(ad, str):
                ad = datetime.date.fromisoformat(ad)
                r["attendance_date"] = ad
            if start_date and ad < start_date:
                continue
            if end_date and ad > end_date:
                continue
            period_records.append(r)

        p_present = sum(1 for r in period_records if r["status"] == "Present")
        p_absent = sum(1 for r in period_records if r["status"] == "Absent")
        p_leave = sum(1 for r in period_records if r["status"] == "Leave")
        p_holiday = sum(1 for r in period_records if r["status"] == "Holiday")
        p_eligible = eligible_days(p_present, p_absent, p_leave)
        p_att_pct = calculate_attendance_percentage(p_present, p_absent, p_leave)
        p_abs_pct = calculate_absenteeism_percentage(p_present, p_absent, p_leave)

        cursor.execute(
            """
            SELECT a.status, COUNT(*) as cnt
            FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE e.department = %s
              AND (%s IS NULL OR a.attendance_date >= %s)
              AND (%s IS NULL OR a.attendance_date <= %s)
            GROUP BY a.status
            """,
            (emp["department"], start_date, start_date, end_date, end_date),
        )
        dept_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
        d_present = dept_counts.get("Present", 0)
        d_absent = dept_counts.get("Absent", 0)
        d_leave = dept_counts.get("Leave", 0)
        d_holiday = dept_counts.get("Holiday", 0)
        d_eligible = eligible_days(d_present, d_absent, d_leave)
        d_att_pct = calculate_attendance_percentage(d_present, d_absent, d_leave)
        d_abs_pct = calculate_absenteeism_percentage(d_present, d_absent, d_leave)

        monthly_map = {}
        for r in all_records:
            ad = r["attendance_date"]
            key = (ad.year, ad.month)
            if key not in monthly_map:
                monthly_map[key] = {"present": 0, "absent": 0, "leave": 0, "holiday": 0}
            st = r["status"]
            if st in monthly_map[key]:
                monthly_map[key][st] += 1

        monthly_trends = []
        for (y, m), counts in sorted(monthly_map.items()):
            m_dt = datetime.date(y, m, 1)
            mp = counts["present"]
            ma = counts["absent"]
            ml = counts["leave"]
            mh = counts["holiday"]
            melig = eligible_days(mp, ma, ml)
            monthly_trends.append({
                "year": y,
                "month": m,
                "label": m_dt.strftime("%b %Y"),
                "present": mp,
                "absent": ma,
                "leave": ml,
                "holiday": mh,
                "eligible_days": melig,
                "attendance_pct": calculate_attendance_percentage(mp, ma, ml),
                "absenteeism_pct": calculate_absenteeism_percentage(mp, ma, ml),
            })

        recent_exceptions = [
            r for r in period_records if r["status"] in ("Absent", "Leave")
        ][:15]

        available_months = get_available_months(conn)

        patterns = analyze_employee_patterns(period_records, monthly_trends)

        return {
            "employee": emp,
            "reporting_period": reporting_period_label,
            "selected_year": year,
            "selected_month": month,
            "available_months": available_months,
            "kpis": {
                "present": p_present,
                "present_count": p_present,
                "absent": p_absent,
                "absent_count": p_absent,
                "leave": p_leave,
                "leave_count": p_leave,
                "holiday": p_holiday,
                "holiday_count": p_holiday,
                "eligible_days": p_eligible,
                "attendance_pct": p_att_pct,
                "absenteeism_pct": p_abs_pct,
            },
            "department_comparison": {
                "department": emp["department"],
                "present": d_present,
                "absent": d_absent,
                "leave": d_leave,
                "holiday": d_holiday,
                "eligible_days": d_eligible,
                "attendance_pct": d_att_pct,
                "absenteeism_pct": d_abs_pct,
            },
            "monthly_trends": monthly_trends,
            "recent_exceptions": recent_exceptions,
            "records": period_records,
            "patterns": patterns,
        }
    finally:
        cursor.close()


def analyze_employee_patterns(
    records: list[dict],
    monthly_trends: list[dict],
    critical_threshold: float = 75.0,
) -> dict[str, Any]:
    """Calculate advanced attendance behavior patterns: streaks, weekdays, and factual insights."""
    sorted_records = sorted(
        records,
        key=lambda r: (
            datetime.date.fromisoformat(r["attendance_date"])
            if isinstance(r["attendance_date"], str)
            else r["attendance_date"]
        ),
    )

    max_streak = 0
    current_streak = 0
    max_streak_start = None
    max_streak_end = None
    cur_streak_start = None

    weekday_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    for r in sorted_records:
        ad = r["attendance_date"]
        if isinstance(ad, str):
            ad = datetime.date.fromisoformat(ad)
        st = r["status"]

        if st == "Absent":
            if ad.weekday() in weekday_counts:
                weekday_counts[ad.weekday()] += 1

            if current_streak == 0:
                cur_streak_start = ad
            current_streak += 1

            if current_streak > max_streak:
                max_streak = current_streak
                max_streak_start = cur_streak_start
                max_streak_end = ad
        else:
            current_streak = 0
            cur_streak_start = None

    sorted_weekdays = sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True)
    top_w_idx, top_w_count = sorted_weekdays[0]
    top_weekday_str = (
        f"{weekday_names[top_w_idx]} ({top_w_count} absence{'s' if top_w_count != 1 else ''})"
        if top_w_count > 0
        else "None (0 absences)"
    )

    months_below = [
        m
        for m in monthly_trends
        if m.get("attendance_pct") is not None and m["attendance_pct"] < critical_threshold
    ]
    below_count = len(months_below)

    trend_description = "Insufficient history for multi-month trend comparison."
    if len(monthly_trends) >= 2:
        prev_m = monthly_trends[-2]
        curr_m = monthly_trends[-1]
        p_pct = prev_m.get("attendance_pct")
        c_pct = curr_m.get("attendance_pct")
        if p_pct is not None and c_pct is not None:
            diff = c_pct - p_pct
            if abs(diff) < 0.05:
                trend_description = (
                    f"Attendance remained steady from {prev_m['label']} ({p_pct:.1f}%) to {curr_m['label']} ({c_pct:.1f}%)."
                )
            elif diff > 0:
                trend_description = (
                    f"Attendance improved by {diff:.1f}% from {prev_m['label']} ({p_pct:.1f}%) to {curr_m['label']} ({c_pct:.1f}%)."
                )
            else:
                trend_description = (
                    f"Attendance declined by {abs(diff):.1f}% from {prev_m['label']} ({p_pct:.1f}%) to {curr_m['label']} ({c_pct:.1f}%)."
                )

    total_absent = sum(1 for r in sorted_records if r["status"] == "Absent")
    summary_parts = []
    if total_absent == 0:
        summary_parts.append("The employee recorded zero absences during the selected reporting period.")
    else:
        summary_parts.append(f"A total of {total_absent} absence(s) were recorded during this period.")
        if max_streak > 1:
            summary_parts.append(f"The maximum consecutive absence streak was {max_streak} day(s).")
        if top_w_count > 1:
            summary_parts.append(
                f"Most frequent absence weekday was {weekday_names[top_w_idx]} ({top_w_count} times)."
            )

    if below_count > 0:
        summary_parts.append(
            f"Attendance dropped below the {critical_threshold:.0f}% threshold in {below_count} month(s)."
        )
    else:
        summary_parts.append(
            f"Attendance consistently satisfied or exceeded the {critical_threshold:.0f}% threshold."
        )

    factual_summary = " ".join(summary_parts)

    return {
        "max_consecutive_absences": max_streak,
        "max_streak_start": max_streak_start,
        "max_streak_end": max_streak_end,
        "weekday_absences": {weekday_names[k]: v for k, v in weekday_counts.items()},
        "top_absent_weekday": top_weekday_str,
        "months_below_threshold": below_count,
        "trend_description": trend_description,
        "factual_summary": factual_summary,
    }


def build_employee_calendar_matrix(
    year: int,
    month: int,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a structured monthly calendar grid annotated with attendance status for visual heatmaps."""
    record_map: dict[datetime.date, dict[str, Any]] = {}
    for r in records:
        ad = r["attendance_date"]
        if isinstance(ad, str):
            ad = datetime.date.fromisoformat(ad)
        record_map[ad] = r

    cal = calendar.monthcalendar(year, month)
    weeks = []
    status_counts: dict[str, int] = {
        "Present": 0,
        "Absent": 0,
        "Leave": 0,
        "Holiday": 0,
        "Weekend": 0,
        "Unrecorded": 0,
    }

    for week in cal:
        week_days = []
        for day in week:
            if day == 0:
                week_days.append({
                    "day": None,
                    "date": None,
                    "is_padding": True,
                    "status": None,
                })
            else:
                d = datetime.date(year, month, day)
                is_weekend = d.weekday() >= 5
                rec = record_map.get(d)
                if rec:
                    st = rec["status"]
                    att_id = rec.get("attendance_id")
                    if st in status_counts:
                        status_counts[st] += 1
                elif is_weekend:
                    st = "Weekend"
                    att_id = None
                    status_counts["Weekend"] += 1
                else:
                    st = "Unrecorded"
                    att_id = None
                    status_counts["Unrecorded"] += 1

                week_days.append({
                    "day": day,
                    "date": d.isoformat(),
                    "weekday": d.weekday(),
                    "is_weekend": is_weekend,
                    "is_padding": False,
                    "status": st,
                    "attendance_id": att_id,
                })
        weeks.append(week_days)

    return {
        "year": year,
        "month": month,
        "month_label": datetime.date(year, month, 1).strftime("%B %Y"),
        "weeks": weeks,
        "status_counts": status_counts,
    }


def get_department_report_data(
    conn: MySQLConnectionAbstract,
    department: str | None = None,
    year: int | None = None,
    month: int | None = None,
    critical_threshold: float = 75.0,
) -> dict[str, Any]:
    """Compile aggregated department-level and employee-wise metrics for reports."""
    import calendar
    from src.calculations import (
        calculate_absenteeism_percentage,
        calculate_attendance_percentage,
        eligible_days,
    )

    clean_dept = (
        department.strip()
        if department and department.strip() and department.strip().lower() != "all"
        else None
    )

    start_date = None
    end_date = None
    reporting_period = "All Time"
    if year is not None and month is not None:
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime.date(year, month, 1)
        end_date = datetime.date(year, month, last_day)
        reporting_period = start_date.strftime("%B %Y")

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)

    if clean_dept:
        df_scoped = df[df["department"] == clean_dept].copy()
    else:
        df_scoped = df.copy()

    total_employees = len(df_scoped["employee_code"].unique()) if not df_scoped.empty else 0

    present_total = int((df_scoped["status"] == "Present").sum()) if not df_scoped.empty else 0
    absent_total = int((df_scoped["status"] == "Absent").sum()) if not df_scoped.empty else 0
    leave_total = int((df_scoped["status"] == "Leave").sum()) if not df_scoped.empty else 0
    holiday_total = int((df_scoped["status"] == "Holiday").sum()) if not df_scoped.empty else 0
    eligible_total = eligible_days(present_total, absent_total, leave_total)

    overall_att_pct = calculate_attendance_percentage(present_total, absent_total, leave_total)
    overall_abs_pct = calculate_absenteeism_percentage(present_total, absent_total, leave_total)

    emp_summary_df = employee_summary(df_scoped)
    dept_summary_df = department_summary(df)

    employee_rows = []
    employees_below = []

    for _, row in emp_summary_df.iterrows():
        att_pct = row["attendance_pct"]
        if att_pct is None:
            warning_level = "NO_DATA"
            warning_label = "No Records"
        elif att_pct < critical_threshold:
            warning_level = "CRITICAL"
            warning_label = "Below 75%"
        elif att_pct < 85.0:
            warning_level = "ATTENTION"
            warning_label = "Attention (75-85%)"
        else:
            warning_level = "NORMAL"
            warning_label = "Normal (>=85%)"

        item = {
            "employee_code": row["employee_code"],
            "employee_name": row["employee_name"],
            "department": row["department"],
            "present": int(row["present"]),
            "absent": int(row["absent"]),
            "leave": int(row["leave"]),
            "holiday": int(row["holiday"]),
            "eligible_days": int(row["eligible_days"]),
            "attendance_pct": att_pct,
            "absenteeism_pct": row["absenteeism_pct"],
            "warning_level": warning_level,
            "warning_label": warning_label,
        }
        employee_rows.append(item)
        if warning_level == "CRITICAL":
            employees_below.append(item)

    return {
        "department": clean_dept or "All Departments",
        "is_all_departments": clean_dept is None,
        "reporting_period": reporting_period,
        "selected_year": year,
        "selected_month": month,
        "total_employees": total_employees,
        "kpis": {
            "present": present_total,
            "absent": absent_total,
            "leave": leave_total,
            "holiday": holiday_total,
            "eligible_days": eligible_total,
            "attendance_pct": overall_att_pct,
            "absenteeism_pct": overall_abs_pct,
        },
        "employee_rows": employee_rows,
        "employees_below_75": employees_below,
        "department_summaries": dept_summary_df.to_dict("records"),
    }



