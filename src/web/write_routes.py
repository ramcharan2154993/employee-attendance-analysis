"""Write routes and form handling for Employee Attendance Analysis System."""

import datetime
from typing import Any
from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
)
from src.attendance import (
    VALID_STATUSES,
    AttendanceConflictError,
    check_department_attendance_conflicts,
    record_attendance,
    record_department_attendance,
    record_holiday,
    update_attendance,
)
from src.employees import (
    add_employee,
    deactivate_employee,
    get_department_employees,
    get_employee,
    list_departments,
    list_employees,
    update_employee,
)
from src.web import get_db, role_required

write_bp = Blueprint("write_routes", __name__)


@write_bp.route("/users/new", methods=["POST"])
@role_required("Admin")
def new_user() -> Any:
    """Create a new user account with role ('Admin' or 'HR')."""
    conn = get_db()
    from src.auth import create_user

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "HR").strip()

    try:
        create_user(conn, username, password, role)
        flash(f"User '{username}' created successfully.")
        return redirect("/users", code=302)
    except ValueError as exc:
        from src.auth import list_users

        users = list_users(conn)
        return (
            render_template(
                "users.html",
                users=users,
                error=f"Error: {exc}",
            ),
            400,
        )


@write_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@role_required("Admin")
def toggle_user(user_id: int) -> Any:
    """Toggle active/inactive status of a user account."""
    conn = get_db()
    from src.auth import toggle_user_status

    try:
        new_status = toggle_user_status(conn, user_id)
        status_text = "activated" if new_status else "deactivated"
        flash(f"User account {status_text}.")
        return redirect("/users", code=302)
    except ValueError as exc:
        from src.auth import list_users

        users = list_users(conn)
        return (
            render_template(
                "users.html",
                users=users,
                error=f"Error: {exc}",
            ),
            400,
        )


@write_bp.route("/employees/new", methods=["GET", "POST"])
def new_employee() -> Any:
    """Render employee creation form and process submissions."""
    if request.method == "POST":
        code = request.form.get("employee_code", "").strip()
        name = request.form.get("employee_name", "").strip()
        dept = request.form.get("department", "").strip()
        j_date = request.form.get("joining_date", "").strip() or None
        email = request.form.get("email", "").strip() or None
        mobile = request.form.get("mobile_number", "").strip() or None
        alt_phone = request.form.get("alt_phone", "").strip() or None
        designation = request.form.get("designation", "").strip() or None

        try:
            conn = get_db()
            add_employee(
                conn,
                code,
                name,
                dept,
                joining_date=j_date,
                email=email,
                mobile_number=mobile,
                alt_phone=alt_phone,
                designation=designation,
            )
            flash(f"Employee {code} added.")
            return redirect("/employees", code=302)
        except ValueError as exc:
            return (
                render_template(
                    "employee_form.html",
                    title="Add Employee",
                    form_action="/employees/new",
                    is_edit=False,
                    code=code,
                    name=name,
                    department=dept,
                    joining_date=j_date or "",
                    email=email or "",
                    mobile_number=mobile or "",
                    alt_phone=alt_phone or "",
                    designation=designation or "",
                    error=f"Error: {exc}",
                ),
                400,
            )

    return render_template(
        "employee_form.html",
        title="Add Employee",
        form_action="/employees/new",
        is_edit=False,
        code="",
        name="",
        department="",
        joining_date=datetime.date.today().isoformat(),
        email="",
        mobile_number="",
        alt_phone="",
        designation="",
        error=None,
    )


@write_bp.route("/employees/<string:code>/edit", methods=["GET", "POST"])
def edit_employee(code: str) -> Any:
    """Render employee editing form and process modifications."""
    conn = get_db()
    emp = get_employee(conn, code.strip())
    if emp is None:
        abort(404)

    emp_code = emp["employee_code"]
    if request.method == "POST":
        name = request.form.get("employee_name", "").strip()
        dept = request.form.get("department", "").strip()
        j_date = request.form.get("joining_date", "").strip() or None
        email = request.form.get("email", "").strip() or None
        mobile = request.form.get("mobile_number", "").strip() or None
        alt_phone = request.form.get("alt_phone", "").strip() or None
        designation = request.form.get("designation", "").strip() or None

        try:
            update_employee(
                conn,
                emp_code,
                employee_name=name,
                department=dept,
                joining_date=j_date,
                email=email,
                mobile_number=mobile,
                alt_phone=alt_phone,
                designation=designation,
                update_contacts=True,
            )
            flash(f"Employee {emp_code} updated.")
            return redirect("/employees", code=302)
        except ValueError as exc:
            return (
                render_template(
                    "employee_form.html",
                    title="Edit Employee",
                    form_action=f"/employees/{emp_code}/edit",
                    is_edit=True,
                    code=emp_code,
                    name=name,
                    department=dept,
                    joining_date=j_date or str(emp["joining_date"]),
                    email=email or "",
                    mobile_number=mobile or "",
                    alt_phone=alt_phone or "",
                    designation=designation or "",
                    error=f"Error: {exc}",
                ),
                400,
            )

    return render_template(
        "employee_form.html",
        title="Edit Employee",
        form_action=f"/employees/{emp_code}/edit",
        is_edit=True,
        code=emp_code,
        name=emp["employee_name"],
        department=emp["department"],
        joining_date=str(emp["joining_date"]),
        email=emp.get("email") or "",
        mobile_number=emp.get("mobile_number") or "",
        alt_phone=emp.get("alt_phone") or "",
        designation=emp.get("designation") or "",
        error=None,
    )


@write_bp.route("/employees/<string:code>/deactivate", methods=["GET", "POST"])
def deactivate_employee_view(code: str) -> Any:
    """Render deactivation confirmation page and process deactivation."""
    conn = get_db()
    emp = get_employee(conn, code.strip())
    if emp is None:
        abort(404)

    emp_code = emp["employee_code"]
    if request.method == "POST":
        confirm = request.form.get("confirm", "").strip()
        if confirm == "YES":
            deactivate_employee(conn, emp_code)
            flash(f"Employee {emp_code} deactivated.")
        else:
            flash("Cancelled.")
        return redirect("/employees", code=302)

    return render_template(
        "deactivate.html",
        employee=emp,
        error=None,
    )


@write_bp.route("/attendance/new", methods=["GET", "POST"])
def new_attendance() -> Any:
    """Render attendance entry form and record daily attendance."""
    conn = get_db()
    if request.method == "POST":
        emp_code = request.form.get("employee_code", "").strip()
        date_str = request.form.get("attendance_date", "").strip()
        status = request.form.get("status", "").strip()
        try:
            try:
                att_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc

            user = g.get("current_user")
            user_id = user.get("user_id") if user else None
            username = user.get("username") if user else None

            record_attendance(
                conn, emp_code, att_date, status, user_id=user_id, username=username
            )
            flash("Attendance recorded.")
            return redirect("/attendance", code=302)
        except ValueError as exc:
            employees = list_employees(conn, include_inactive=False)
            return (
                render_template(
                    "attendance_form.html",
                    title="Record Attendance",
                    form_action="/attendance/new",
                    valid_statuses=VALID_STATUSES,
                    employee_code=emp_code,
                    attendance_date=date_str,
                    status=status,
                    employees=employees,
                    error=f"Error: {exc}",
                ),
                400,
            )

    emp_code = request.args.get("employee_code", request.args.get("employee", "")).strip()
    date_str = request.args.get("attendance_date", request.args.get("date", "")).strip()
    if not date_str:
        date_str = datetime.date.today().isoformat()
    employees = list_employees(conn, include_inactive=False)

    return render_template(
        "attendance_form.html",
        title="Record Attendance",
        form_action="/attendance/new",
        valid_statuses=VALID_STATUSES,
        employee_code=emp_code,
        attendance_date=date_str,
        status="Present",
        employees=employees,
        error=None,
    )


@write_bp.route("/attendance/correct", methods=["GET", "POST"])
def correct_attendance() -> Any:
    """Render attendance correction form and modify recorded status with audit trail."""
    conn = get_db()
    if request.method == "POST":
        emp_code = request.form.get("employee_code", "").strip()
        date_str = request.form.get("attendance_date", "").strip()
        status = request.form.get("status", "").strip()
        reason = request.form.get("reason", "").strip()

        if "reason" in request.form and not reason:
            employees = list_employees(conn, include_inactive=False)
            return (
                render_template(
                    "attendance_form.html",
                    title="Correct Attendance",
                    form_action="/attendance/correct",
                    valid_statuses=VALID_STATUSES,
                    employee_code=emp_code,
                    attendance_date=date_str,
                    status=status,
                    reason="",
                    employees=employees,
                    error="Error: A correction reason is required.",
                ),
                400,
            )

        effective_reason = reason or "Administrative correction"
        try:
            try:
                att_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc

            user = g.get("current_user")
            user_id = user.get("user_id") if user else None
            username = user.get("username") if user else None

            update_attendance(
                conn,
                emp_code,
                att_date,
                status,
                reason=effective_reason,
                user_id=user_id,
                username=username,
            )
            flash(f"Attendance for {emp_code} on {att_date} corrected to {status}.")
            return redirect(f"/attendance?view=log&employee={emp_code}", code=302)
        except ValueError as exc:
            employees = list_employees(conn, include_inactive=False)
            return (
                render_template(
                    "attendance_form.html",
                    title="Correct Attendance",
                    form_action="/attendance/correct",
                    valid_statuses=VALID_STATUSES,
                    employee_code=emp_code,
                    attendance_date=date_str,
                    status=status,
                    reason=reason,
                    employees=employees,
                    error=f"Error: {exc}",
                ),
                400,
            )

    emp_code = request.args.get("employee_code", request.args.get("employee", "")).strip()
    date_str = request.args.get("attendance_date", request.args.get("date", "")).strip()
    if not date_str:
        date_str = datetime.date.today().isoformat()
    employees = list_employees(conn, include_inactive=False)

    return render_template(
        "attendance_form.html",
        title="Correct Attendance",
        form_action="/attendance/correct",
        valid_statuses=VALID_STATUSES,
        employee_code=emp_code,
        attendance_date=date_str,
        status="Present",
        reason="",
        employees=employees,
        error=None,
    )


@write_bp.route("/attendance/department", methods=["GET", "POST"])
def department_attendance() -> Any:
    """Render department bulk attendance form and record batch attendance atomically."""
    conn = get_db()
    departments = list_departments(conn)

    if request.method == "POST":
        dept = request.form.get("department", "").strip()
        date_str = request.form.get("attendance_date", "").strip()

        entries = []
        codes = request.form.getlist("employee_codes")
        if not codes:
            for key, val in request.form.items():
                if key.startswith("status_"):
                    code = key[7:]
                    entries.append({"employee_code": code, "status": val.strip()})
        else:
            for code in codes:
                st = request.form.get(f"status_{code}", "").strip()
                entries.append({"employee_code": code, "status": st})

        att_date = None
        try:
            try:
                att_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc

            user = g.get("current_user")
            user_id = user.get("user_id") if user else None
            username = user.get("username") if user else None

            res = record_department_attendance(
                conn, dept, att_date, entries, user_id=user_id, username=username
            )
            flash(
                f"Successfully recorded attendance for {res['total_records']} employee(s) in {dept} on {att_date} "
                f"({res['present_count']} Present, {res['absent_count']} Absent, {res['leave_count']} Leave)."
            )
            return redirect(
                f"/attendance?view=log&department={dept}&start={date_str}&end={date_str}",
                code=302,
            )
        except (ValueError, AttendanceConflictError) as exc:
            conflicts = getattr(exc, "conflicts", [])
            if not conflicts and dept and att_date:
                conflicts = check_department_attendance_conflicts(conn, dept, att_date)

            eligible_employees = []
            unrecorded_employees = []
            conflict_codes = {c["employee_code"] for c in conflicts}
            if dept and att_date:
                try:
                    eligible_employees = get_department_employees(
                        conn, dept, active_only=True, eligible_as_of=att_date
                    )
                    unrecorded_employees = [
                        e
                        for e in eligible_employees
                        if e["employee_code"] not in conflict_codes
                    ]
                except Exception:
                    pass

            submitted_map = {e["employee_code"]: e["status"] for e in entries}
            return (
                render_template(
                    "department_attendance.html",
                    departments=departments,
                    selected_department=dept,
                    attendance_date=date_str,
                    eligible_employees=eligible_employees,
                    unrecorded_employees=unrecorded_employees,
                    recorded_employees=conflicts,
                    submitted_statuses=submitted_map,
                    conflicts=conflicts,
                    error=f"Error: {exc}",
                ),
                400,
            )

    # GET Request
    dept = request.args.get("department", "").strip()
    date_str = request.args.get("attendance_date", request.args.get("date", "")).strip()
    if not date_str:
        date_str = datetime.date.today().isoformat()

    att_date = None
    date_error = None
    try:
        att_date = datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        date_error = f"Invalid date: '{date_str}'"

    if att_date and att_date.weekday() >= 5:
        date_error = f"Attendance cannot be recorded on weekends ({att_date})."

    eligible_employees = []
    unrecorded_employees = []
    recorded_employees = []
    conflicts = []
    dept_error = None

    if dept and not date_error and att_date:
        if dept not in departments:
            dept_error = (
                f"Department '{dept}' does not exist or has no active employees."
            )
        else:
            try:
                eligible_employees = get_department_employees(
                    conn, dept, active_only=True, eligible_as_of=att_date
                )
                conflicts = check_department_attendance_conflicts(conn, dept, att_date)
                conflict_codes = {c["employee_code"] for c in conflicts}
                recorded_employees = conflicts
                unrecorded_employees = [
                    e
                    for e in eligible_employees
                    if e["employee_code"] not in conflict_codes
                ]
            except Exception as exc:
                dept_error = f"Error: {exc}"

    return render_template(
        "department_attendance.html",
        departments=departments,
        selected_department=dept,
        attendance_date=date_str,
        eligible_employees=eligible_employees,
        unrecorded_employees=unrecorded_employees,
        recorded_employees=recorded_employees,
        submitted_statuses={},
        conflicts=conflicts,
        error=date_error or dept_error,
    )


@write_bp.route("/holidays/new", methods=["GET", "POST"])
def new_holiday() -> Any:
    """Render holiday recording form and record organization holidays."""
    if request.method == "POST":
        date_str = request.form.get("holiday_date", "").strip()
        try:
            try:
                h_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc
            conn = get_db()
            user = g.get("current_user")
            user_id = user.get("user_id") if user else None
            username = user.get("username") if user else None

            count = record_holiday(conn, h_date, user_id=user_id, username=username)
            flash(f"Holiday recorded for {count} employees.")
            return redirect("/attendance?view=log", code=302)
        except ValueError as exc:
            return (
                render_template(
                    "holiday_form.html",
                    title="Record Holiday",
                    form_action="/holidays/new",
                    holiday_date=date_str,
                    error=f"Error: {exc}",
                ),
                400,
            )

    return render_template(
        "holiday_form.html",
        title="Record Holiday",
        form_action="/holidays/new",
        holiday_date="",
        error=None,
    )


@write_bp.route("/alerts/<int:alert_id>/review", methods=["POST"])
def review_alert(alert_id: int) -> Any:
    """Mark an attendance warning as reviewed with optional reviewer notes."""
    conn = get_db()
    from src.alerts import mark_alert_reviewed

    notes = request.form.get("notes", "").strip()
    user = g.get("current_user")
    reviewer_id = user.get("user_id") if user else None

    try:
        mark_alert_reviewed(conn, alert_id, user_id=reviewer_id, notes=notes)
        flash("Alert successfully marked as reviewed.")
    except Exception as exc:
        flash(f"Error reviewing alert: {exc}")

    redirect_to = request.form.get("return_url") or request.referrer or "/alerts"
    return redirect(redirect_to, code=302)


@write_bp.route("/alerts/settings/threshold", methods=["POST"])
@role_required("Admin")
def update_threshold() -> Any:
    """Update critical attendance threshold in system_settings (Admin only)."""
    conn = get_db()
    from src.alerts import set_critical_threshold

    threshold_str = request.form.get("threshold", "").strip()
    try:
        val = float(threshold_str)
        set_critical_threshold(conn, val)
        flash(f"Critical attendance warning threshold updated to {val:.1f}%.")
    except ValueError as exc:
        flash(f"Invalid threshold value: {exc}")

    return redirect(request.referrer or "/alerts", code=302)


@write_bp.route("/alerts/sync", methods=["POST"])
def sync_alerts() -> Any:
    """Synchronize monthly attendance alerts on demand."""
    import calendar
    conn = get_db()
    from src.alerts import sync_monthly_attendance_alerts

    year_str = request.form.get("year", "2026").strip()
    month_str = request.form.get("month", "9").strip()
    try:
        year = int(year_str)
        month = int(month_str)
        count = sync_monthly_attendance_alerts(conn, year, month)
        flash(f"Synchronized {count} alerts for {calendar.month_name[month]} {year}.")
    except Exception as exc:
        flash(f"Failed to synchronize alerts: {exc}")

    return redirect(f"/alerts?year={year}&month={month}", code=302)



