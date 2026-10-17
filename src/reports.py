"""Report formatting and chart export module."""

import calendar
import datetime
from pathlib import Path
import pandas as pd
from mysql.connector.abstracts import MySQLConnectionAbstract
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    load_attendance_df,
    monthly_summary,
)
from src.calculations import calculate_attendance_percentage, format_percentage
from src.visualizations import (
    save_absenteeism_chart,
    save_monthly_attendance_chart,
)


def format_employee_report(summary_df: pd.DataFrame) -> str:
    """Format employee summary DataFrame into a plain-text table."""
    if summary_df.empty:
        return "No employee data to report."

    lines = [
        f"{'Code':<8} {'Name':<20} {'Department':<15} {'Present':>8} {'Absent':>8} {'Leave':>8} {'Holiday':>8} {'Eligible':>10} {'Attendance':>12} {'Absenteeism':>12}",
        "-" * 115,
    ]
    for row in summary_df.itertuples(index=False):
        att_str = format_percentage(
            None if pd.isna(row.attendance_pct) else row.attendance_pct
        )
        abs_str = format_percentage(
            None if pd.isna(row.absenteeism_pct) else row.absenteeism_pct
        )
        lines.append(
            f"{row.employee_code:<8} {row.employee_name:<20} {row.department:<15} {row.present:>8} {row.absent:>8} {row.leave:>8} {row.holiday:>8} {row.eligible_days:>10} {att_str:>12} {abs_str:>12}"
        )
    return "\n".join(lines)


def format_department_report(dept_df: pd.DataFrame) -> str:
    """Format department summary DataFrame into a plain-text table."""
    if dept_df.empty:
        return "No department data to report."

    lines = [
        f"{'Department':<20} {'Present':>8} {'Absent':>8} {'Leave':>8} {'Holiday':>8} {'Eligible':>10} {'Attendance':>12} {'Absenteeism':>12}",
        "-" * 94,
    ]
    for row in dept_df.itertuples(index=False):
        att_str = format_percentage(
            None if pd.isna(row.attendance_pct) else row.attendance_pct
        )
        abs_str = format_percentage(
            None if pd.isna(row.absenteeism_pct) else row.absenteeism_pct
        )
        lines.append(
            f"{row.department:<20} {row.present:>8} {row.absent:>8} {row.leave:>8} {row.holiday:>8} {row.eligible_days:>10} {att_str:>12} {abs_str:>12}"
        )
    return "\n".join(lines)


def format_absenteeism_report(ranking_df: pd.DataFrame) -> str:
    """Format absenteeism ranking DataFrame into a plain-text table."""
    if ranking_df.empty:
        return "No absenteeism data to report."

    lines = [
        f"{'Code':<8} {'Name':<20} {'Department':<15} {'Absent':>8} {'Eligible':>10} {'Absenteeism':>12}",
        "-" * 77,
    ]
    for row in ranking_df.itertuples(index=False):
        abs_str = format_percentage(
            None if pd.isna(row.absenteeism_pct) else row.absenteeism_pct
        )
        lines.append(
            f"{row.employee_code:<8} {row.employee_name:<20} {row.department:<15} {row.absent:>8} {row.eligible_days:>10} {abs_str:>12}"
        )
    return "\n".join(lines)


def generate_monthly_report(
    conn: MySQLConnectionAbstract,
    year: int,
    month: int,
) -> str:
    """Generate a formatted monthly attendance report including employee and department summaries."""
    if month < 1 or month > 12:
        raise ValueError(f"Month must be between 1 and 12, got: {month}")

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    has_records = not df.empty and df["attendance_date"].notna().any()
    if not has_records:
        return f"No attendance records for {year:04d}-{month:02d}."

    emp_summary_df = employee_summary(df)
    dept_summary_df = department_summary(df)

    total_present = int((df["status"] == "Present").sum())
    total_absent = int((df["status"] == "Absent").sum())
    total_leave = int((df["status"] == "Leave").sum())
    total_holiday = int((df["status"] == "Holiday").sum())
    total_eligible = total_present + total_absent + total_leave
    overall_att_pct = calculate_attendance_percentage(
        total_present, total_absent, total_leave
    )
    overall_att_str = format_percentage(overall_att_pct)

    sections = [
        f"Monthly attendance report: {year:04d}-{month:02d}",
        "",
        "Employee Summary:",
        format_employee_report(emp_summary_df),
        "",
        "Department Summary:",
        format_department_report(dept_summary_df),
        "",
        "Totals:",
        f"Total present: {total_present}",
        f"Total absent: {total_absent}",
        f"Total leave: {total_leave}",
        f"Total holiday: {total_holiday}",
        f"Total eligible days: {total_eligible}",
        f"Overall attendance: {overall_att_str}",
    ]
    return "\n".join(sections)


def export_charts(
    conn: MySQLConnectionAbstract,
    year: int,
    month: int,
    output_dir: str = "output",
) -> list[Path]:
    """Save monthly absenteeism ranking chart and overall monthly trend chart to PNG files."""
    if month < 1 or month > 12:
        raise ValueError(f"Month must be between 1 and 12, got: {month}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _, last_day = calendar.monthrange(year, month)
    month_df = load_attendance_df(
        conn,
        start_date=datetime.date(year, month, 1),
        end_date=datetime.date(year, month, last_day),
    )
    month_ranking = absenteeism_ranking(employee_summary(month_df))
    chart1_path = out_dir / f"absenteeism_{year:04d}-{month:02d}.png"
    save_absenteeism_chart(
        month_ranking,
        chart1_path,
        f"Absenteeism Ranking - {year:04d}-{month:02d}",
    )

    all_df = load_attendance_df(conn)
    trend_summary = monthly_summary(all_df)
    chart2_path = out_dir / "monthly_attendance.png"
    save_monthly_attendance_chart(
        trend_summary,
        chart2_path,
        "Monthly Attendance Trends",
    )

    return [chart1_path, chart2_path]
