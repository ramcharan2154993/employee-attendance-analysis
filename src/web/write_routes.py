"""Write routes and form handling for Employee Attendance Analysis System."""

import datetime
from typing import Any
from flask import (
    Blueprint,
    abort,
    flash,
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
from src.web import get_db

write_bp = Blueprint("write_routes", __name__)


@write_bp.route("/employees/new", methods=["GET", "POST"])
def new_employee() -> Any:
    """Render employee creation form and process submissions."""
    if request.method == "POST":
        code = request.form.get("employee_code", "").strip()
        name = request.form.get("employee_name", "").strip()
        dept = request.form.get("department", "").strip()
        j_date = request.form.get("joining_date", "").strip() or None
        try:
            conn = get_db()
            add_employee(conn, code, name, dept, joining_date=j_date)
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
        try:
            update_employee(
                conn,
                emp_code,
                employee_name=name,
                department=dept,
                joining_date=j_date,
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
            record_attendance(conn, emp_code, att_date, status)
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
    """Render attendance correction form and modify recorded status."""
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
            update_attendance(conn, emp_code, att_date, status)
            flash("Attendance corrected.")
            return redirect("/attendance", code=302)
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

            res = record_department_attendance(conn, dept, att_date, entries)
            flash(
                f"Successfully recorded attendance for {res['total_records']} employee(s) in {dept} on {att_date} "
                f"({res['present_count']} Present, {res['absent_count']} Absent, {res['leave_count']} Leave)."
            )
            return redirect(f"/attendance?department={dept}&start={date_str}&end={date_str}", code=302)
        except (ValueError, AttendanceConflictError) as exc:
            conflicts = getattr(exc, "conflicts", [])
            if not conflicts and dept and att_date:
                conflicts = check_department_attendance_conflicts(conn, dept, att_date)

            eligible_employees = []
            if dept and att_date:
                try:
                    eligible_employees = get_department_employees(
                        conn, dept, active_only=True, eligible_as_of=att_date
                    )
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
    conflicts = []
    dept_error = None

    if dept and not date_error and att_date:
        if dept not in departments:
            dept_error = f"Department '{dept}' does not exist or has no active employees."
        else:
            try:
                eligible_employees = get_department_employees(
                    conn, dept, active_only=True, eligible_as_of=att_date
                )
                conflicts = check_department_attendance_conflicts(conn, dept, att_date)
            except Exception as exc:
                dept_error = f"Error: {exc}"

    return render_template(
        "department_attendance.html",
        departments=departments,
        selected_department=dept,
        attendance_date=date_str,
        eligible_employees=eligible_employees,
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
            count = record_holiday(conn, h_date)
            flash(f"Holiday recorded for {count} employees.")
            return redirect("/attendance", code=302)
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

