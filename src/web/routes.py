"""Web routes for Employee Attendance Analysis System."""

import datetime
from pathlib import Path
import re
from typing import Any
from flask import (
    Blueprint,
    abort,
    current_app,
    render_template,
    request,
    send_from_directory,
)
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    get_dashboard_summary,
    load_attendance_df,
)
from src.attendance import get_attendance
from src.employees import (
    get_recent_employees,
    list_departments,
    list_employees,
    search_employees,
)
from src.reports import (
    export_charts,
    format_absenteeism_report,
    format_department_report,
    format_employee_report,
    generate_monthly_report,
)
from src.web import get_db

bp = Blueprint("routes", __name__)


def _parse_date_filters() -> tuple[datetime.date | None, datetime.date | None]:
    """Parse start and end query parameters as dates."""
    start_str = request.args.get("start", "").strip()
    end_str = request.args.get("end", "").strip()
    start_date = None
    if start_str:
        try:
            start_date = datetime.date.fromisoformat(start_str)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid start date: '{start_str}'") from exc
    end_date = None
    if end_str:
        try:
            end_date = datetime.date.fromisoformat(end_str)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid end date: '{end_str}'") from exc
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")
    return start_date, end_date


@bp.route("/", methods=["GET"])
def index() -> str:
    """Render home dashboard displaying active employee count, KPIs, charts, and recent staff."""
    conn = get_db()
    active_employees = list_employees(conn, include_inactive=False)
    active_count = len(active_employees)
    metrics = get_dashboard_summary(conn)
    recent_employees = get_recent_employees(conn, limit=5)

    output_dir = current_app.config["OUTPUT_DIR"]
    chart_path = Path(output_dir) / "monthly_attendance.png"
    if not chart_path.exists():
        try:
            export_charts(conn, metrics["year"], metrics["month"], output_dir=output_dir)
        except Exception:
            pass
    has_chart = chart_path.exists()

    return render_template(
        "index.html",
        active_count=active_count,
        metrics=metrics,
        recent_employees=recent_employees,
        has_chart=has_chart,
    )



@bp.route("/employees", methods=["GET"])
def employees_view() -> str:
    """Render employees list with search and inactive inclusion filters."""
    conn = get_db()
    q = request.args.get("q", "").strip()
    include_inactive = request.args.get("include_inactive") == "1"
    if q:
        employees = search_employees(conn, q, include_inactive=include_inactive)
    else:
        employees = list_employees(conn, include_inactive=include_inactive)
    return render_template(
        "employees.html",
        employees=employees,
        q=q,
        include_inactive=include_inactive,
    )


@bp.route("/attendance", methods=["GET"])
def attendance_view() -> str:
    """Render attendance log with optional employee, department, and date range filters."""
    conn = get_db()
    emp_code = request.args.get("employee", "").strip() or None
    dept_filter = request.args.get("department", "").strip() or None
    start_str = request.args.get("start", "").strip()
    end_str = request.args.get("end", "").strip()

    start_date = None
    if start_str:
        try:
            start_date = datetime.date.fromisoformat(start_str)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid start date: '{start_str}'") from exc

    end_date = None
    if end_str:
        try:
            end_date = datetime.date.fromisoformat(end_str)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid end date: '{end_str}'") from exc

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    departments = list_departments(conn)
    employees = list_employees(conn, include_inactive=True, department=dept_filter)
    records = get_attendance(
        conn,
        employee_code=emp_code,
        start_date=start_date,
        end_date=end_date,
        department=dept_filter,
    )
    return render_template(
        "attendance.html",
        records=records,
        employee=emp_code or "",
        department=dept_filter or "",
        departments=departments,
        employees=employees,
        start=start_str,
        end=end_str,
    )


@bp.route("/summary/employees", methods=["GET"])
def summary_employees_view() -> str:
    """Render formatted employee summary table inside a preformatted block."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    report_text = format_employee_report(summary_df)
    return render_template(
        "text_report.html",
        title="Employee Summary",
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/summary/departments", methods=["GET"])
def summary_departments_view() -> str:
    """Render formatted department summary table inside a preformatted block."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = department_summary(df)
    report_text = format_department_report(summary_df)
    return render_template(
        "text_report.html",
        title="Department Summary",
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/ranking", methods=["GET"])
def ranking_view() -> str:
    """Render formatted absenteeism ranking table inside a preformatted block."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    ranking_df = absenteeism_ranking(summary_df)
    report_text = format_absenteeism_report(ranking_df)
    return render_template(
        "text_report.html",
        title="Absenteeism Ranking",
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/report", methods=["GET"])
def report_view() -> str:
    """Render monthly attendance report text inside a preformatted block."""
    conn = get_db()
    year_str = request.args.get("year", "").strip()
    month_str = request.args.get("month", "").strip()
    if not year_str and not month_str:
        year = 2026
        month = 9
    else:
        try:
            year = int(year_str)
            month = int(month_str)
        except (ValueError, TypeError) as exc:
            raise ValueError("Year and month must be valid numbers.") from exc

    report_text = generate_monthly_report(conn, year, month)
    return render_template(
        "text_report.html",
        title=f"Monthly Report - {year:04d}-{month:02d}",
        report_text=report_text,
        year=year,
        month=month,
    )


@bp.route("/charts", methods=["GET"])
def charts_view() -> str:
    """Render charts view displaying exported monthly PNG images."""
    conn = get_db()
    year_str = request.args.get("year", "").strip()
    month_str = request.args.get("month", "").strip()
    if not year_str and not month_str:
        year = 2026
        month = 9
    else:
        try:
            year = int(year_str)
            month = int(month_str)
        except (ValueError, TypeError) as exc:
            raise ValueError("Year and month must be valid numbers.") from exc

    output_dir = current_app.config["OUTPUT_DIR"]
    export_charts(conn, year, month, output_dir=output_dir)
    chart1 = f"absenteeism_{year:04d}-{month:02d}.png"
    chart2 = "monthly_attendance.png"
    return render_template(
        "charts.html",
        year=year,
        month=month,
        chart1=chart1,
        chart2=chart2,
    )


@bp.route("/charts/file/<path:filename>", methods=["GET"])
def serve_chart_file(filename: str) -> Any:
    """Safely serve generated chart PNG files matching strictly validated filenames."""
    if not re.match(
        r"^(absenteeism_[0-9]{4}-[0-9]{2}|monthly_attendance)\.png$", filename
    ):
        abort(404)
    output_dir = Path(current_app.config["OUTPUT_DIR"]).resolve()
    return send_from_directory(output_dir, filename)
