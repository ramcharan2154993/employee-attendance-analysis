"""Employee management module."""

import datetime
import os
from typing import Any
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract


def add_employee(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    employee_name: str,
    department: str,
    joining_date: datetime.date | str | None = None,
) -> int:
    """Add a new active employee to the database and return their employee_id."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")
    if not employee_name or not employee_name.strip():
        raise ValueError("Employee name cannot be blank.")
    if not department or not department.strip():
        raise ValueError("Department cannot be blank.")

    resolved_joining_date: datetime.date
    if joining_date is None:
        default_env = os.getenv("DEFAULT_JOINING_DATE")
        if default_env:
            resolved_joining_date = datetime.date.fromisoformat(default_env.strip())
        else:
            resolved_joining_date = datetime.date.today()
    elif isinstance(joining_date, str):
        try:
            resolved_joining_date = datetime.date.fromisoformat(joining_date.strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid joining date '{joining_date}'. Expected format: YYYY-MM-DD."
            ) from exc
    elif isinstance(joining_date, datetime.date):
        resolved_joining_date = joining_date
    else:
        raise ValueError(f"Invalid joining date type: {type(joining_date)}.")

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO employees (employee_code, employee_name, department, is_active, joining_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                employee_code.strip(),
                employee_name.strip(),
                department.strip(),
                True,
                resolved_joining_date,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            raise ValueError(
                f"Employee with code '{employee_code.strip()}' already exists."
            ) from err
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_employee(
    conn: MySQLConnectionAbstract,
    employee_code: str,
) -> dict | None:
    """Retrieve an employee record by employee_code, or None if not found."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date
            FROM employees
            WHERE employee_code = %s
            """,
            (employee_code.strip(),),
        )
        row = cursor.fetchone()
        if row is not None:
            row["is_active"] = bool(row["is_active"])
        return row
    finally:
        cursor.close()


def list_employees(
    conn: MySQLConnectionAbstract,
    include_inactive: bool = False,
    department: str | None = None,
) -> list[dict]:
    """List employees ordered by employee_code, optionally including inactive employees and filtering by department."""
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date
            FROM employees
            WHERE (%s = TRUE OR is_active = TRUE)
              AND (%s IS NULL OR department = %s)
            ORDER BY employee_code
        """
        dept_val = department.strip() if department and department.strip() else None
        cursor.execute(query, (include_inactive, dept_val, dept_val))
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


def search_employees(
    conn: MySQLConnectionAbstract,
    text: str,
    include_inactive: bool = False,
) -> list[dict]:
    """Search employees by matching text in employee_code, employee_name, or department, respecting active status."""
    if not text or not text.strip():
        return []

    pattern = f"%{text.strip()}%"
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date
            FROM employees
            WHERE (employee_code LIKE %s OR employee_name LIKE %s OR department LIKE %s)
              AND (%s = TRUE OR is_active = TRUE)
            ORDER BY employee_code
            """,
            (pattern, pattern, pattern, include_inactive),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


def list_departments(conn: MySQLConnectionAbstract) -> list[str]:
    """Return a sorted list of unique department names from active employees."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT DISTINCT department FROM employees WHERE is_active = TRUE ORDER BY department"
        )
        return [row[0] for row in cursor.fetchall() if row[0]]
    finally:
        cursor.close()


def get_department_employees(
    conn: MySQLConnectionAbstract,
    department: str,
    active_only: bool = True,
    eligible_as_of: datetime.date | None = None,
) -> list[dict]:
    """Retrieve employees in a department, optionally filtering by active status and joining date."""
    if not department or not department.strip():
        raise ValueError("Department cannot be blank.")

    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date
            FROM employees
            WHERE department = %s
        """
        params: list[Any] = [department.strip()]
        if active_only:
            query += " AND is_active = TRUE"
        if eligible_as_of is not None:
            query += " AND joining_date <= %s"
            params.append(eligible_as_of)
        query += " ORDER BY employee_code"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


def update_employee(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    employee_name: str | None = None,
    department: str | None = None,
    joining_date: datetime.date | str | None = None,
) -> None:
    """Update name, department, and/or joining date of an existing employee."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")
    if employee_name is not None and not employee_name.strip():
        raise ValueError("Employee name cannot be blank.")
    if department is not None and not department.strip():
        raise ValueError("Department cannot be blank.")

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_name, department, joining_date FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        current = cursor.fetchone()
        if not current:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")

        current_name, current_dept, current_joining_date = current
        new_name = employee_name.strip() if employee_name is not None else current_name
        new_dept = department.strip() if department is not None else current_dept

        new_joining_date: datetime.date
        if joining_date is not None:
            if isinstance(joining_date, str):
                try:
                    new_joining_date = datetime.date.fromisoformat(joining_date.strip())
                except (ValueError, TypeError) as exc:
                    raise ValueError(
                        f"Invalid joining date '{joining_date}'. Expected format: YYYY-MM-DD."
                    ) from exc
            elif isinstance(joining_date, datetime.date):
                new_joining_date = joining_date
            else:
                raise ValueError(f"Invalid joining date type: {type(joining_date)}.")
        else:
            new_joining_date = current_joining_date

        cursor.execute(
            """
            UPDATE employees
            SET employee_name = %s, department = %s, joining_date = %s
            WHERE employee_code = %s
            """,
            (new_name, new_dept, new_joining_date, employee_code.strip()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def deactivate_employee(
    conn: MySQLConnectionAbstract,
    employee_code: str,
) -> None:
    """Deactivate an employee by setting is_active to FALSE."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE employees
            SET is_active = FALSE
            WHERE employee_code = %s
            """,
            (employee_code.strip(),),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_recent_employees(
    conn: MySQLConnectionAbstract,
    limit: int = 5,
) -> list[dict]:
    """Retrieve recently joined active employees ordered by joining_date DESC, employee_id DESC."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT employee_id, employee_code, employee_name, department, is_active, joining_date
            FROM employees
            WHERE is_active = TRUE
            ORDER BY joining_date DESC, employee_id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


