"""Employee management module."""

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract


def add_employee(
    conn: MySQLConnectionAbstract,
    employee_code: str,
    employee_name: str,
    department: str,
) -> int:
    """Add a new active employee to the database and return their employee_id."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")
    if not employee_name or not employee_name.strip():
        raise ValueError("Employee name cannot be blank.")
    if not department or not department.strip():
        raise ValueError("Department cannot be blank.")

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO employees (employee_code, employee_name, department, is_active)
            VALUES (%s, %s, %s, %s)
            """,
            (employee_code.strip(), employee_name.strip(), department.strip(), True),
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
            SELECT employee_id, employee_code, employee_name, department, is_active
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
) -> list[dict]:
    """List employees ordered by employee_code, optionally including inactive employees."""
    cursor = conn.cursor(dictionary=True)
    try:
        if include_inactive:
            cursor.execute(
                """
                SELECT employee_id, employee_code, employee_name, department, is_active
                FROM employees
                ORDER BY employee_code
                """
            )
        else:
            cursor.execute(
                """
                SELECT employee_id, employee_code, employee_name, department, is_active
                FROM employees
                WHERE is_active = TRUE
                ORDER BY employee_code
                """
            )
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


def search_employees(
    conn: MySQLConnectionAbstract,
    text: str,
) -> list[dict]:
    """Search employees by matching text in employee_code, employee_name, or department."""
    if not text or not text.strip():
        return []

    pattern = f"%{text.strip()}%"
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT employee_id, employee_code, employee_name, department, is_active
            FROM employees
            WHERE employee_code LIKE %s OR employee_name LIKE %s OR department LIKE %s
            ORDER BY employee_code
            """,
            (pattern, pattern, pattern),
        )
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
) -> None:
    """Update name and/or department of an existing employee."""
    if not employee_code or not employee_code.strip():
        raise ValueError("Employee code cannot be blank.")
    if employee_name is not None and not employee_name.strip():
        raise ValueError("Employee name cannot be blank.")
    if department is not None and not department.strip():
        raise ValueError("Department cannot be blank.")

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT employee_name, department FROM employees WHERE employee_code = %s",
            (employee_code.strip(),),
        )
        current = cursor.fetchone()
        if not current:
            raise ValueError(f"Employee '{employee_code.strip()}' not found.")

        current_name, current_dept = current
        new_name = employee_name.strip() if employee_name is not None else current_name
        new_dept = department.strip() if department is not None else current_dept

        cursor.execute(
            """
            UPDATE employees
            SET employee_name = %s, department = %s
            WHERE employee_code = %s
            """,
            (new_name, new_dept, employee_code.strip()),
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
