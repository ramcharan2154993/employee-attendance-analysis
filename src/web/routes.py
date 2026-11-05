"""Web routes for Employee Attendance Analysis System."""

import calendar
import datetime
import io
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
    send_file,
    send_from_directory,
    session,
    url_for,
)
from src.analysis import (
    absenteeism_ranking,
    analyze_employee_patterns,
    build_employee_calendar_matrix,
    department_summary,
    employee_summary,
    get_available_months,
    get_dashboard_summary,
    get_department_report_data,
    get_employee_analytics_data,
    load_attendance_df,
)
from src.attendance import count_attendance, get_attendance
from src.calculations import (
    calculate_absenteeism_percentage,
    calculate_attendance_percentage,
    eligible_days,
    format_percentage,
)
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
from src.alerts import (
    classify_attendance_level,
    count_attendance_alerts,
    get_alert_metrics_summary,
    get_critical_threshold,
    list_attendance_alerts,
    sync_monthly_attendance_alerts,
)

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


@bp.route("/healthz", methods=["GET"])
def healthz() -> Any:
    """Lightweight health check endpoint returning 'ok' without database access or info leak."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}


@bp.route("/welcome", methods=["GET"])
def landing() -> Any:
    """Public marketing landing page (no DB access, no employee data)."""
    return render_template("landing.html")


@bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Render login page and process session authentication."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next", "").strip()

        from src.rate_limiter import login_limiter
        client_ip = request.remote_addr or "127.0.0.1"

        blocked, remaining_sec, reason = login_limiter.check_login_attempt(client_ip, username)
        if blocked:
            minutes = (remaining_sec + 59) // 60
            scope_desc = "from your IP address" if reason == "ip" else "for this account"
            return (
                render_template(
                    "login.html",
                    error=f"Too many failed login attempts {scope_desc}. Please try again in {minutes} minute(s).",
                    username=username,
                    next=next_url,
                ),
                429,
            )

        conn = get_db()
        from src.auth import authenticate_user

        user = authenticate_user(conn, username, password)
        if not user:
            is_blocked, remaining_sec, reason = login_limiter.register_login_failure(client_ip, username)
            if is_blocked:
                minutes = (remaining_sec + 59) // 60
                scope_desc = "from your IP address" if reason == "ip" else "for this account"
                err_msg = f"Too many failed login attempts {scope_desc}. Account temporarily locked for {minutes} minute(s)."
                status_code = 429
            else:
                err_msg = "Invalid username or password."
                status_code = 401
            return (
                render_template(
                    "login.html",
                    error=err_msg,
                    username=username,
                    next=next_url,
                ),
                status_code,
            )

        login_limiter.register_login_success(client_ip, username)
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

    # Executive alert summary & department health breakdown
    threshold = get_critical_threshold(conn)
    try:
        sync_monthly_attendance_alerts(conn, metrics["year"], metrics["month"])
    except Exception:
        pass

    alert_metrics = get_alert_metrics_summary(conn, metrics["year"], metrics["month"])
    recent_alerts = list_attendance_alerts(
        conn,
        year=metrics["year"],
        month=metrics["month"],
        limit=5,
    )
    dept_report = get_department_report_data(
        conn,
        department=None,
        year=metrics["year"],
        month=metrics["month"],
        critical_threshold=threshold,
    )

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
        threshold=threshold,
        alert_metrics=alert_metrics,
        recent_alerts=recent_alerts,
        departments=dept_report.get("department_summaries", []),
        low_attendants=dept_report.get("employees_below_75", []),
    )




@bp.route("/employees", methods=["GET"])
def employees_view() -> str:
    """Render employees list with search, department, and employment status filters."""
    conn = get_db()
    q = request.args.get("q", "").strip()
    include_inactive = request.args.get("include_inactive") == "1"
    dept_filter = request.args.get("department", "").strip() or None
    status_filter = request.args.get("status", "").strip()

    effective_include_inactive = include_inactive or status_filter in ("inactive", "all")

    if q:
        employees = search_employees(
            conn, q, include_inactive=effective_include_inactive, department=dept_filter
        )
    else:
        employees = list_employees(
            conn, include_inactive=effective_include_inactive, department=dept_filter
        )

    if status_filter == "inactive":
        employees = [e for e in employees if not e["is_active"]]
    elif status_filter == "active":
        employees = [e for e in employees if e["is_active"]]

    departments = list_departments(conn)
    return render_template(
        "employees.html",
        employees=employees,
        q=q,
        include_inactive=include_inactive,
        selected_department=dept_filter,
        status_filter=status_filter,
        departments=departments,
    )


def build_employee_analytics_data(
    conn: Any,
    employee_id_or_code: int | str,
    filter_period: str = "all",
) -> dict[str, Any]:
    """Build complete analytics metrics, breakdowns, benchmarks, and trends for an employee."""
    all_employees = list_employees(conn, include_inactive=True)
    emp = None
    if isinstance(employee_id_or_code, int):
        for e in all_employees:
            if e["employee_id"] == employee_id_or_code:
                emp = e
                break
    else:
        target_str = str(employee_id_or_code).strip()
        if target_str.isdigit():
            target_id = int(target_str)
            for e in all_employees:
                if e["employee_id"] == target_id:
                    emp = e
                    break
        if emp is None:
            for e in all_employees:
                if e["employee_code"].upper() == target_str.upper():
                    emp = e
                    break

    if emp is None:
        raise ValueError(f"Employee '{employee_id_or_code}' not found.")

    emp_id = emp["employee_id"]
    emp_code = emp["employee_code"]
    dept = emp["department"]

    # Validate filter_period
    period_str = (filter_period or "all").strip()
    req_year = None
    req_month = None
    if period_str and period_str.lower() != "all":
        m = re.match(r"^(\d{4})-(\d{2})$", period_str)
        if not m:
            raise ValueError(f"Invalid period format: '{period_str}'. Expected 'all' or 'YYYY-MM'.")
        req_year = int(m.group(1))
        req_month = int(m.group(2))
        if req_month < 1 or req_month > 12:
            raise ValueError(f"Invalid month: {req_month}. Month must be between 1 and 12.")

    # Fetch all records for this employee
    all_emp_records = get_attendance(conn, employee_code=emp_code, order_asc=True)

    # Group by (year, month)
    monthly_groups: dict[tuple[int, int], list[dict]] = {}
    for r in all_emp_records:
        ad = r["attendance_date"]
        if isinstance(ad, str):
            ad = datetime.date.fromisoformat(ad)
            r["attendance_date"] = ad
        key = (ad.year, ad.month)
        if key not in monthly_groups:
            monthly_groups[key] = []
        monthly_groups[key].append(r)

    # Monthly breakdown (one row per month in which this employee has at least one row)
    monthly_trends = []
    for (y, m) in sorted(monthly_groups.keys(), reverse=True):
        m_recs = monthly_groups[(y, m)]
        mp = sum(1 for r in m_recs if r["status"] == "Present")
        ma = sum(1 for r in m_recs if r["status"] == "Absent")
        ml = sum(1 for r in m_recs if r["status"] == "Leave")
        mh = sum(1 for r in m_recs if r["status"] == "Holiday")
        melig = eligible_days(mp, ma, ml)
        m_dt = datetime.date(y, m, 1)
        m_label = m_dt.strftime("%b %Y")
        ym_str = f"{y:04d}-{m:02d}"
        monthly_trends.append({
            "year": y,
            "month": m,
            "period": ym_str,
            "label": m_label,
            "present": mp,
            "absent": ma,
            "leave": ml,
            "holiday": mh,
            "eligible_days": melig,
            "attendance_pct": calculate_attendance_percentage(mp, ma, ml),
            "absenteeism_pct": calculate_absenteeism_percentage(mp, ma, ml),
        })

    # Available months for dropdown: newest first
    available_months = [(m["period"], m["label"]) for m in monthly_trends]

    # Recalculate KPIs for selected period
    if req_year is not None and req_month is not None:
        selected_period_label = datetime.date(req_year, req_month, 1).strftime("%b %Y")
        period_records = [
            r for r in all_emp_records
            if r["attendance_date"].year == req_year and r["attendance_date"].month == req_month
        ]
        selected_period_val = f"{req_year:04d}-{req_month:02d}"
    else:
        selected_period_label = "All Time"
        period_records = all_emp_records
        selected_period_val = "all"

    p_present = sum(1 for r in period_records if r["status"] == "Present")
    p_absent = sum(1 for r in period_records if r["status"] == "Absent")
    p_leave = sum(1 for r in period_records if r["status"] == "Leave")
    p_holiday = sum(1 for r in period_records if r["status"] == "Holiday")
    p_eligible = eligible_days(p_present, p_absent, p_leave)
    p_att_pct = calculate_attendance_percentage(p_present, p_absent, p_leave)
    p_abs_pct = calculate_absenteeism_percentage(p_present, p_absent, p_leave)

    # Department benchmark for chosen period
    if req_year is not None and req_month is not None:
        _, last_day = calendar.monthrange(req_year, req_month)
        d_start = datetime.date(req_year, req_month, 1)
        d_end = datetime.date(req_year, req_month, last_day)
        dept_records = get_attendance(conn, department=dept, start_date=d_start, end_date=d_end)
    else:
        dept_records = get_attendance(conn, department=dept)

    d_present = sum(1 for r in dept_records if r["status"] == "Present")
    d_absent = sum(1 for r in dept_records if r["status"] == "Absent")
    d_leave = sum(1 for r in dept_records if r["status"] == "Leave")
    d_holiday = sum(1 for r in dept_records if r["status"] == "Holiday")
    d_eligible = eligible_days(d_present, d_absent, d_leave)
    d_att_pct = calculate_attendance_percentage(d_present, d_absent, d_leave)
    d_abs_pct = calculate_absenteeism_percentage(d_present, d_absent, d_leave)

    explanation = f"{dept} department, {selected_period_label}: {d_absent} absent out of {d_eligible} eligible days across all its employees."

    # Monthly trends for chart: sorted chronologically (oldest to newest)
    chart_trends = sorted(monthly_trends, key=lambda item: (item["year"], item["month"]))

    recent_exceptions = [
        r for r in period_records if r["status"] in ("Absent", "Leave")
    ][:15]

    threshold = get_critical_threshold(conn)
    patterns = analyze_employee_patterns(
        period_records,
        monthly_trends,
        critical_threshold=threshold,
    )

    # Determine calendar month to display
    if req_year is not None and req_month is not None:
        cal_year = req_year
        cal_month = req_month
    elif monthly_trends:
        latest_trend = monthly_trends[0]
        cal_year = latest_trend["year"]
        cal_month = latest_trend["month"]
    else:
        cal_year = 2026
        cal_month = 9

    cal_records = [
        r for r in all_emp_records
        if r["attendance_date"].year == cal_year and r["attendance_date"].month == cal_month
    ]
    calendar_matrix = build_employee_calendar_matrix(cal_year, cal_month, cal_records)

    warning_level, warning_label = classify_attendance_level(
        p_att_pct,
        critical_threshold=threshold,
    )

    return {
        "employee": emp,
        "reporting_period": selected_period_label,
        "selected_period": selected_period_val,
        "selected_year": req_year,
        "selected_month": req_month,
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
            "department": dept,
            "present": d_present,
            "absent": d_absent,
            "leave": d_leave,
            "holiday": d_holiday,
            "eligible_days": d_eligible,
            "attendance_pct": d_att_pct,
            "absenteeism_pct": d_abs_pct,
            "explanation": explanation,
        },
        "monthly_trends": monthly_trends,
        "chart_trends": chart_trends,
        "recent_exceptions": recent_exceptions,
        "records": period_records,
        "patterns": patterns,
        "calendar_matrix": calendar_matrix,
        "warning_level": warning_level,
        "warning_label": warning_label,
        "threshold": threshold,
    }


@bp.route("/employees/<int:employee_id>", methods=["GET"])
@bp.route("/employees/<int:employee_id>/analytics", methods=["GET"])
def employee_analytics_view(employee_id: int) -> str:
    """Render comprehensive analytics profile for an individual employee."""
    conn = get_db()
    from src.visualizations import (
        save_employee_distribution_chart,
        save_employee_trend_chart,
    )

    filter_period = request.args.get("filter_period", "").strip()
    if not filter_period:
        year_str = request.args.get("year", "").strip()
        month_str = request.args.get("month", "").strip()
        if year_str and month_str:
            try:
                y = int(year_str)
                m = int(month_str)
                filter_period = f"{y:04d}-{m:02d}"
            except (ValueError, TypeError):
                return render_template("error.html", message="Error: Year and month must be valid numbers."), 400
        else:
            filter_period = "all"

    try:
        analytics_data = build_employee_analytics_data(
            conn, employee_id, filter_period=filter_period
        )
    except ValueError as exc:
        return render_template("error.html", message=f"Error: {exc}"), 400

    output_dir = Path(current_app.config["OUTPUT_DIR"])
    trend_filename = f"emp_{employee_id}_trend.png"
    dist_filename = f"emp_{employee_id}_dist.png"

    try:
        save_employee_trend_chart(
            analytics_data["chart_trends"],
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


@bp.route("/employees/<int:employee_id>/report/pdf", methods=["GET"])
def employee_report_pdf_download(employee_id: int) -> Any:
    """Download individual employee attendance statement as a publication-grade PDF."""
    conn = get_db()
    period = request.args.get("period", "").strip() or None
    year = None
    month = None

    if period and period != "all":
        parts = period.split("-")
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                pass

    from src.employees import get_employee_by_id

    emp = get_employee_by_id(conn, employee_id)
    if not emp:
        abort(404)

    from src.reports_pdf import generate_employee_pdf_report

    pdf_bytes = generate_employee_pdf_report(conn, employee_id, year=year, month=month)
    period_str = f"{year:04d}_{month:02d}" if year and month else "all_time"
    filename = f"Attendance_Report_{emp['employee_code']}_{period_str}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/employees/<int:employee_id>/report/excel", methods=["GET"])
def employee_report_excel_download(employee_id: int) -> Any:
    """Download individual employee attendance spreadsheet (.xlsx)."""
    conn = get_db()
    period = request.args.get("period", "").strip() or None
    year = None
    month = None

    if period and period != "all":
        parts = period.split("-")
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                pass

    from src.employees import get_employee_by_id

    emp = get_employee_by_id(conn, employee_id)
    if not emp:
        abort(404)

    from src.reports_excel import generate_employee_excel_report

    excel_bytes = generate_employee_excel_report(conn, employee_id, year=year, month=month)
    period_str = f"{year:04d}_{month:02d}" if year and month else "all_time"
    filename = f"Attendance_Report_{emp['employee_code']}_{period_str}.xlsx"

    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/reports/department/pdf", methods=["GET"])
@bp.route("/department/report/pdf", methods=["GET"])
def department_report_pdf_download() -> Any:
    """Download department-wide or organization-wide attendance audit report as PDF."""
    conn = get_db()
    department = request.args.get("department", "").strip() or None
    period = request.args.get("period", "").strip() or None
    year = None
    month = None

    if period and period != "all":
        parts = period.split("-")
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                pass
    else:
        year_str = request.args.get("year", "").strip()
        month_str = request.args.get("month", "").strip()
        if year_str and month_str:
            try:
                year = int(year_str)
                month = int(month_str)
            except ValueError:
                pass

    from src.reports_pdf import generate_department_pdf_report

    pdf_bytes = generate_department_pdf_report(conn, department=department, year=year, month=month)
    dept_slug = department.replace(" ", "_") if department else "All_Departments"
    period_str = f"{year:04d}_{month:02d}" if year and month else "all_time"
    filename = f"Department_Attendance_{dept_slug}_{period_str}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/reports/department/excel", methods=["GET"])
@bp.route("/department/report/excel", methods=["GET"])
def department_report_excel_download() -> Any:
    """Download department-wide or organization-wide attendance report as Excel spreadsheet (.xlsx)."""
    conn = get_db()
    department = request.args.get("department", "").strip() or None
    period = request.args.get("period", "").strip() or None
    year = None
    month = None

    if period and period != "all":
        parts = period.split("-")
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
            except ValueError:
                pass
    else:
        year_str = request.args.get("year", "").strip()
        month_str = request.args.get("month", "").strip()
        if year_str and month_str:
            try:
                year = int(year_str)
                month = int(month_str)
            except ValueError:
                pass

    from src.reports_excel import generate_department_excel_report

    excel_bytes = generate_department_excel_report(conn, department=department, year=year, month=month)
    dept_slug = department.replace(" ", "_") if department else "All_Departments"
    period_str = f"{year:04d}_{month:02d}" if year and month else "all_time"
    filename = f"Department_Attendance_{dept_slug}_{period_str}.xlsx"

    return send_file(
        io.BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
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
    """Render designed employee summary page with KPI cards and interactive table."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    report_text = format_employee_report(summary_df)

    rows = summary_df.to_dict("records") if not summary_df.empty else []
    total_present = int(summary_df["present"].sum()) if not summary_df.empty else 0
    total_absent = int(summary_df["absent"].sum()) if not summary_df.empty else 0
    total_leave = int(summary_df["leave"].sum()) if not summary_df.empty else 0
    total_holiday = int(summary_df["holiday"].sum()) if not summary_df.empty else 0
    total_eligible = int(summary_df["eligible_days"].sum()) if not summary_df.empty else 0
    total_employees = len(summary_df)

    overall_att = calculate_attendance_percentage(total_present, total_absent, total_leave)
    overall_abs = calculate_absenteeism_percentage(total_present, total_absent, total_leave)

    return render_template(
        "text_report.html",
        report_type="employee_summary",
        title="Employee Summary",
        rows=rows,
        total_employees=total_employees,
        total_eligible=total_eligible,
        total_present=total_present,
        total_absent=total_absent,
        total_leave=total_leave,
        total_holiday=total_holiday,
        overall_att=overall_att,
        overall_abs=overall_abs,
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/summary/departments", methods=["GET"])
def summary_departments_view() -> str:
    """Render designed department summary page with department cards and full table."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    dept_df = department_summary(df)
    report_text = format_department_report(dept_df)
    rows = dept_df.to_dict("records") if not dept_df.empty else []

    total_present = int(dept_df["present"].sum()) if not dept_df.empty else 0
    total_absent = int(dept_df["absent"].sum()) if not dept_df.empty else 0
    total_leave = int(dept_df["leave"].sum()) if not dept_df.empty else 0
    total_holiday = int(dept_df["holiday"].sum()) if not dept_df.empty else 0
    total_eligible = int(dept_df["eligible_days"].sum()) if not dept_df.empty else 0
    total_depts = len(dept_df)

    overall_att = calculate_attendance_percentage(total_present, total_absent, total_leave)
    overall_abs = calculate_absenteeism_percentage(total_present, total_absent, total_leave)

    return render_template(
        "text_report.html",
        report_type="department_summary",
        title="Department Summary",
        rows=rows,
        total_depts=total_depts,
        total_eligible=total_eligible,
        total_present=total_present,
        total_absent=total_absent,
        total_leave=total_leave,
        total_holiday=total_holiday,
        overall_att=overall_att,
        overall_abs=overall_abs,
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/ranking", methods=["GET"])
def ranking_view() -> str:
    """Render designed absenteeism ranking page with rank badges and rates."""
    conn = get_db()
    start_date, end_date = _parse_date_filters()
    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    summary_df = employee_summary(df)
    ranking_df = absenteeism_ranking(summary_df)
    report_text = format_absenteeism_report(ranking_df)
    rows = ranking_df.to_dict("records") if not ranking_df.empty else []

    total_ranked = len(rows)
    total_absent = int(ranking_df["absent"].sum()) if not ranking_df.empty and "absent" in ranking_df.columns else 0
    total_eligible = int(ranking_df["eligible_days"].sum()) if not ranking_df.empty and "eligible_days" in ranking_df.columns else 0

    return render_template(
        "text_report.html",
        report_type="ranking",
        title="Absenteeism Ranking",
        rows=rows,
        total_ranked=total_ranked,
        total_absent=total_absent,
        total_eligible=total_eligible,
        report_text=report_text,
        start=start_date.isoformat() if start_date else "",
        end=end_date.isoformat() if end_date else "",
    )


@bp.route("/report", methods=["GET"])
def report_view() -> str:
    """Render designed monthly report page with KPI cards and detailed tables."""
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
            if month < 1 or month > 12:
                return render_template("error.html", message=f"Error: Month must be between 1 and 12, got: {month}"), 400
        except (ValueError, TypeError):
            return render_template("error.html", message="Error: Year and month must be valid numbers."), 400

    months_list = get_available_months(conn)
    available_years = sorted(list(set(y for y, _, _ in months_list)), reverse=True)
    if not available_years:
        available_years = [2026]
    if year not in available_years:
        available_years = sorted(list(set(available_years + [year])), reverse=True)

    _, last_day = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    df = load_attendance_df(conn, start_date=start_date, end_date=end_date)
    has_records = not df.empty and df["attendance_date"].notna().any()

    if not has_records:
        empty_sentence = f"No attendance records for {year:04d}-{month:02d}."
        return render_template(
            "text_report.html",
            report_type="monthly",
            title=f"Monthly Report - {year:04d}-{month:02d}",
            has_records=False,
            empty_sentence=empty_sentence,
            year=year,
            month=month,
            available_years=available_years,
            report_text=empty_sentence,
        )

    emp_summary_df = employee_summary(df)
    dept_summary_df = department_summary(df)

    emp_rows = emp_summary_df.to_dict("records")
    dept_rows = dept_summary_df.to_dict("records")

    total_present = int((df["status"] == "Present").sum())
    total_absent = int((df["status"] == "Absent").sum())
    total_leave = int((df["status"] == "Leave").sum())
    total_holiday = int((df["status"] == "Holiday").sum())
    total_eligible = total_present + total_absent + total_leave
    overall_att = calculate_attendance_percentage(total_present, total_absent, total_leave)
    overall_att_str = format_percentage(overall_att)

    report_text = generate_monthly_report(conn, year, month)

    return render_template(
        "text_report.html",
        report_type="monthly",
        title=f"Monthly Report - {year:04d}-{month:02d}",
        has_records=True,
        year=year,
        month=month,
        available_years=available_years,
        emp_rows=emp_rows,
        dept_rows=dept_rows,
        total_present=total_present,
        total_absent=total_absent,
        total_leave=total_leave,
        total_holiday=total_holiday,
        total_eligible=total_eligible,
        overall_att=overall_att,
        overall_att_str=overall_att_str,
        report_text=report_text,
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
            if month < 1 or month > 12:
                return render_template("error.html", message=f"Error: Month must be between 1 and 12, got: {month}"), 400
        except (ValueError, TypeError):
            return render_template("error.html", message="Error: Year and month must be valid numbers."), 400

    months_list = get_available_months(conn)
    available_years = sorted(list(set(y for y, _, _ in months_list)), reverse=True)
    if not available_years:
        available_years = [2026]
    if year not in available_years:
        available_years = sorted(list(set(available_years + [year])), reverse=True)

    output_dir = current_app.config["OUTPUT_DIR"]
    export_charts(conn, year, month, output_dir=output_dir)
    chart1 = f"absenteeism_{year:04d}-{month:02d}.png"
    chart2 = "monthly_attendance.png"
    return render_template(
        "charts.html",
        year=year,
        month=month,
        available_years=available_years,
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


@bp.route("/alerts", methods=["GET"])
def alerts_dashboard() -> Any:
    """Render smart attendance warning center with multi-tier alerts and review tracking."""
    conn = get_db()

    months_list = get_available_months(conn)
    available_years = sorted(list(set(y for y, _, _ in months_list)), reverse=True)
    if not available_years:
        available_years = [2026]

    year_str = request.args.get("year", "").strip()
    month_str = request.args.get("month", "").strip()
    dept = request.args.get("department", "").strip() or None
    level = request.args.get("level", "").strip() or None
    reviewed_param = request.args.get("reviewed", "").strip().lower()
    page_str = request.args.get("page", "1").strip()

    is_reviewed: bool | None = None
    if reviewed_param == "true":
        is_reviewed = True
    elif reviewed_param == "false":
        is_reviewed = False

    try:
        page = max(1, int(page_str))
    except (ValueError, TypeError):
        page = 1
    per_page = 25
    offset = (page - 1) * per_page

    year: int | None = None
    month: int | None = None
    if year_str:
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            year = None
    if month_str:
        try:
            month = int(month_str)
        except (ValueError, TypeError):
            month = None

    if year is None and month is None:
        if months_list:
            year, month, _ = months_list[0]
        else:
            year, month = 2026, 9

    # Idempotent sync for selected period
    if year and month:
        sync_monthly_attendance_alerts(conn, year, month)

    threshold = get_critical_threshold(conn)
    metrics = get_alert_metrics_summary(conn, year, month)
    alerts = list_attendance_alerts(
        conn,
        year=year,
        month=month,
        department=dept,
        warning_level=level,
        is_reviewed=is_reviewed,
        limit=per_page,
        offset=offset,
    )
    total_count = count_attendance_alerts(
        conn,
        year=year,
        month=month,
        department=dept,
        warning_level=level,
        is_reviewed=is_reviewed,
    )
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    departments = list_departments(conn)

    return render_template(
        "alerts.html",
        alerts=alerts,
        metrics=metrics,
        threshold=threshold,
        selected_year=year,
        selected_month=month,
        selected_dept=dept or "all",
        selected_level=level or "all",
        selected_reviewed=reviewed_param or "all",
        available_years=available_years,
        departments=departments,
        current_page=page,
        total_pages=total_pages,
        total_count=total_count,
        months_list=months_list,
    )
