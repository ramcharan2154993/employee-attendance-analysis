"""Web routes for Employee Attendance Analysis System."""

import datetime
from pathlib import Path
import re
from typing import Any
from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    get_available_months,
    get_dashboard_summary,
    get_employee_analytics_data,
    load_attendance_df,
)
from src.attendance import count_attendance, get_attendance
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
from src.web import get_db, login_required, role_required

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


@bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Render login page and process session authentication."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next", "").strip()

        conn = get_db()
        from src.auth import authenticate_user

        user = authenticate_user(conn, username, password)
        if not user:
            return (
                render_template(
                    "login.html",
                    error="Invalid username or password.",
                    username=username,
                    next=next_url,
                ),
                401,
            )

        session.clear()
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session.permanent = True

        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url, code=302)
        return redirect("/", code=302)

    next_url = request.args.get("next", "").strip()
    return render_template("login.html", next=next_url, error=None)


@bp.route("/logout", methods=["GET", "POST"])
def logout() -> Any:
    """Clear session and redirect to login page."""
    session.clear()
    return redirect(url_for("routes.login"), code=302)


@bp.route("/", methods=["GET"])
def index() -> str:
    """Render home dashboard displaying active employee count, KPIs, charts, and recent staff."""
    conn = get_db()
    active_employees = list_employees(conn, include_inactive=False)
    active_count = len(active_employees)

    available_months = get_available_months(conn)
    year_str = request.args.get("year", "").strip()
    month_str = request.args.get("month", "").strip()
    req_year = None
    req_month = None
    if year_str or month_str:
        try:
            req_year = int(year_str) if year_str else 2026
            req_month = int(month_str) if month_str else 9
            if req_month < 1 or req_month > 12:
                raise ValueError("Month must be between 1 and 12.")
        except (ValueError, TypeError) as exc:
            raise ValueError("Year and month must be valid numbers.") from exc

    metrics = get_dashboard_summary(conn, year=req_year, month=req_month)
    recent_employees = get_recent_employees(conn, limit=5)

    output_dir = current_app.config["OUTPUT_DIR"]
    try:
        export_charts(conn, metrics["year"], metrics["month"], output_dir=output_dir)
    except Exception:
        pass

    chart_month_file = f"absenteeism_{metrics['year']:04d}-{metrics['month']:02d}.png"
    has_chart = (Path(output_dir) / "monthly_attendance.png").exists()
    has_month_chart = (Path(output_dir) / chart_month_file).exists()

    return render_template(
        "index.html",
        active_count=active_count,
        metrics=metrics,
        recent_employees=recent_employees,
        available_months=available_months,
        has_chart=has_chart,
        has_month_chart=has_month_chart,
        chart_month_file=chart_month_file,
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


@bp.route("/employees/<int:employee_id>/analytics", methods=["GET"])
def employee_analytics_view(employee_id: int) -> str:
    """Render comprehensive analytics profile for an individual employee."""
    conn = get_db()
    from src.visualizations import (
        save_employee_distribution_chart,
        save_employee_trend_chart,
    )

    year_str = request.args.get("year", "").strip()
    month_str = request.args.get("month", "").strip()
    req_year = None
    req_month = None
    if year_str and month_str:
        try:
            req_year = int(year_str)
            req_month = int(month_str)
        except (ValueError, TypeError) as exc:
            raise ValueError("Year and month must be valid numbers.") from exc

    analytics_data = get_employee_analytics_data(
        conn, employee_id, year=req_year, month=req_month
    )

    output_dir = Path(current_app.config["OUTPUT_DIR"])
    trend_filename = f"emp_{employee_id}_trend.png"
    dist_filename = f"emp_{employee_id}_dist.png"

    try:
        save_employee_trend_chart(
            analytics_data["monthly_trends"],
            output_dir / trend_filename,
            f"Monthly Attendance Trend - {analytics_data['employee']['employee_name']}",
        )
        kpis = analytics_data["kpis"]
        save_employee_distribution_chart(
            kpis["present"],
            kpis["absent"],
            kpis["leave"],
            kpis["holiday"],
            output_dir / dist_filename,
            f"Attendance Distribution ({analytics_data['reporting_period']})",
        )
    except Exception as exc:
        current_app.logger.warning("Could not generate employee chart: %s", exc)

    return render_template(
        "employee_analytics.html",
        data=analytics_data,
        trend_chart=trend_filename,
        dist_chart=dist_filename,
    )


@bp.route("/attendance", methods=["GET"])
def attendance_view() -> str:
    """Render attendance landing page with clear actions and on-demand filtered/paginated logs."""
    conn = get_db()
    emp_code = request.args.get("employee", "").strip() or None
    dept_filter = request.args.get("department", "").strip() or None
    status_filter = request.args.get("status", "").strip() or None
    search_q = request.args.get("q", "").strip() or None
    view_mode = request.args.get("view", "").strip()
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

    page_str = request.args.get("page", "1").strip()
    try:
        page = max(1, int(page_str))
    except (ValueError, TypeError):
        page = 1
    per_page = 50
    offset = (page - 1) * per_page

    departments = list_departments(conn)
    employees = list_employees(conn, include_inactive=True, department=dept_filter)

    has_searched = bool(
        emp_code
        or dept_filter
        or status_filter
        or search_q
        or start_date
        or end_date
        or view_mode == "log"
    )

    records = None
    total_records = 0
    total_pages = 1

    if has_searched:
        total_records = count_attendance(
            conn,
            employee_code=emp_code,
            start_date=start_date,
            end_date=end_date,
            department=dept_filter,
            status=status_filter,
            search_query=search_q,
        )
        total_pages = max(1, (total_records + per_page - 1) // per_page)
        records = get_attendance(
            conn,
            employee_code=emp_code,
            start_date=start_date,
            end_date=end_date,
            department=dept_filter,
            status=status_filter,
            search_query=search_q,
            limit=per_page,
            offset=offset,
        )

    return render_template(
        "attendance.html",
        records=records,
        has_searched=has_searched,
        total_records=total_records,
        page=page,
        total_pages=total_pages,
        employee=emp_code or "",
        department=dept_filter or "",
        status=status_filter or "",
        q=search_q or "",
        departments=departments,
        employees=employees,
        start=start_str,
        end=end_str,
    )


@bp.route("/users", methods=["GET"])
@role_required("Admin")
def users_view() -> str:
    """List system users for account and role administration."""
    conn = get_db()
    from src.auth import list_users

    users = list_users(conn)
    return render_template("users.html", users=users)


@bp.route("/audit", methods=["GET"])
@role_required("Admin", "HR")
def audit_view() -> str:
    """Display immutable audit logs of attendance creation and corrections."""
    conn = get_db()
    from src.audit import count_audit_records, get_audit_trail

    emp_code = request.args.get("employee", "").strip() or None
    action_type = request.args.get("action", "").strip() or None
    start_date, end_date = _parse_date_filters()

    page_str = request.args.get("page", "1").strip()
    try:
        page = max(1, int(page_str))
    except (ValueError, TypeError):
        page = 1
    per_page = 50
    offset = (page - 1) * per_page

    total_records = count_audit_records(
        conn,
        employee_code=emp_code,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
    )
    total_pages = max(1, (total_records + per_page - 1) // per_page)

    records = get_audit_trail(
        conn,
        employee_code=emp_code,
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
        limit=per_page,
        offset=offset,
    )

    return render_template(
        "audit.html",
        records=records,
        total_records=total_records,
        page=page,
        total_pages=total_pages,
        employee=emp_code or "",
        action=action_type or "",
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
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
        r"^(absenteeism_[0-9]{4}-[0-9]{2}|monthly_attendance|emp_[0-9]+_(trend|dist))\.png$",
        filename,
    ):
        abort(404)
    output_dir = Path(current_app.config["OUTPUT_DIR"]).resolve()
    response = send_from_directory(output_dir, filename)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response
