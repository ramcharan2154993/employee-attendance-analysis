"""Tests for employee management operations."""

import pytest
import src.employees
from src.employees import (
    add_employee,
    deactivate_employee,
    get_employee,
    list_employees,
    search_employees,
    update_employee,
)


def test_add_and_get_employee(conn):
    """Add then get returns the right code, name, department, is_active true."""
    emp_id = add_employee(conn, "E001", "Asha Rao", "Engineering")
    assert isinstance(emp_id, int)

    emp = get_employee(conn, "E001")
    assert emp is not None
    assert emp["employee_code"] == "E001"
    assert emp["employee_name"] == "Asha Rao"
    assert emp["department"] == "Engineering"
    assert emp["is_active"] is True


def test_duplicate_employee_code_refused(conn):
    """Duplicate employee_code is refused and only 1 row exists."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")

    with pytest.raises(ValueError):
        add_employee(conn, "E001", "Duplicate Rao", "Sales")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees")
    assert cur.fetchone()[0] == 1
    cur.close()


def test_blank_fields_refused(conn):
    """Blank code, blank name and blank department are each refused."""
    with pytest.raises(ValueError):
        add_employee(conn, "", "Asha Rao", "Engineering")
    with pytest.raises(ValueError):
        add_employee(conn, "   ", "Asha Rao", "Engineering")

    with pytest.raises(ValueError):
        add_employee(conn, "E001", "", "Engineering")
    with pytest.raises(ValueError):
        add_employee(conn, "E001", "   ", "Engineering")

    with pytest.raises(ValueError):
        add_employee(conn, "E001", "Asha Rao", "")
    with pytest.raises(ValueError):
        add_employee(conn, "E001", "Asha Rao", "   ")


def test_sql_injection_safety(conn):
    """A name like O'Brien; DROP TABLE employees;-- is stored exactly as typed and table still works."""
    special_name = "O'Brien; DROP TABLE employees;--"
    add_employee(conn, "E001", special_name, "Engineering")

    emp = get_employee(conn, "E001")
    assert emp is not None
    assert emp["employee_name"] == special_name

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees")
    assert cur.fetchone()[0] == 1
    cur.close()


def test_search_employees(conn):
    """Search by part of a name finds the employee; a search with no match returns an empty list."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")

    matches = search_employees(conn, "Rao")
    assert len(matches) == 1
    assert matches[0]["employee_code"] == "E001"

    no_match = search_employees(conn, "NonexistentName")
    assert no_match == []


def test_update_employee(conn):
    """Update changes the department; update of a missing code is refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    update_employee(conn, "E001", department="Management")

    emp = get_employee(conn, "E001")
    assert emp is not None
    assert emp["department"] == "Management"

    with pytest.raises(ValueError):
        update_employee(conn, "E999", department="Management")

    with pytest.raises(ValueError):
        update_employee(conn, "E001", department="   ")


def test_deactivate_and_list_employees(conn):
    """Deactivate sets is_active false; list_employees() hides them; include_inactive shows them; missing code refused."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")

    deactivate_employee(conn, "E001")

    emp = get_employee(conn, "E001")
    assert emp is not None
    assert emp["is_active"] is False

    active_list = list_employees(conn)
    assert len(active_list) == 1
    assert active_list[0]["employee_code"] == "E002"

    all_list = list_employees(conn, include_inactive=True)
    assert len(all_list) == 2

    with pytest.raises(ValueError):
        deactivate_employee(conn, "E999")


def test_module_has_no_delete_employee():
    """The module has no attribute named delete_employee."""
    assert not hasattr(src.employees, "delete_employee")
