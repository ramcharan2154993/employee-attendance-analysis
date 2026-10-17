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
    record_attendance,
    record_holiday,
    update_attendance,
)
from src.employees import (
    add_employee,
    deactivate_employee,
    get_employee,
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
        try:
            conn = get_db()
            add_employee(conn, code, name, dept)
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
        try:
            update_employee(
                conn,
                emp_code,
                employee_name=name,
                department=dept,
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
    if request.method == "POST":
        emp_code = request.form.get("employee_code", "").strip()
        date_str = request.form.get("attendance_date", "").strip()
        status = request.form.get("status", "").strip()
        try:
            try:
                att_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc
            conn = get_db()
            record_attendance(conn, emp_code, att_date, status)
            flash("Attendance recorded.")
            return redirect("/attendance", code=302)
        except ValueError as exc:
            return (
                render_template(
                    "attendance_form.html",
                    title="Record Attendance",
                    form_action="/attendance/new",
                    valid_statuses=VALID_STATUSES,
                    employee_code=emp_code,
                    attendance_date=date_str,
                    status=status,
                    error=f"Error: {exc}",
                ),
                400,
            )

    return render_template(
        "attendance_form.html",
        title="Record Attendance",
        form_action="/attendance/new",
        valid_statuses=VALID_STATUSES,
        employee_code="",
        attendance_date="",
        status="Present",
        error=None,
    )


@write_bp.route("/attendance/correct", methods=["GET", "POST"])
def correct_attendance() -> Any:
    """Render attendance correction form and modify recorded status."""
    if request.method == "POST":
        emp_code = request.form.get("employee_code", "").strip()
        date_str = request.form.get("attendance_date", "").strip()
        status = request.form.get("status", "").strip()
        try:
            try:
                att_date = datetime.date.fromisoformat(date_str)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid date: '{date_str}'") from exc
            conn = get_db()
            update_attendance(conn, emp_code, att_date, status)
            flash("Attendance corrected.")
            return redirect("/attendance", code=302)
        except ValueError as exc:
            return (
                render_template(
                    "attendance_form.html",
                    title="Correct Attendance",
                    form_action="/attendance/correct",
                    valid_statuses=VALID_STATUSES,
                    employee_code=emp_code,
                    attendance_date=date_str,
                    status=status,
                    error=f"Error: {exc}",
                ),
                400,
            )

    return render_template(
        "attendance_form.html",
        title="Correct Attendance",
        form_action="/attendance/correct",
        valid_statuses=VALID_STATUSES,
        employee_code="",
        attendance_date="",
        status="Present",
        error=None,
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
