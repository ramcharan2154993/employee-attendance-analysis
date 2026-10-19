import datetime
import pytest
import src.employees
from src.employees import (
    add_employee,
    deactivate_employee,
    get_department_employees,
    get_employee,
    list_departments,
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


def test_add_employee_with_explicit_joining_date(conn):
    """Adding employee with explicit date stores and retrieves the joining date."""
    join_date = datetime.date(2026, 4, 15)
    emp_id = add_employee(conn, "E010", "Devika Iyer", "Finance", joining_date=join_date)
    assert isinstance(emp_id, int)

    emp = get_employee(conn, "E010")
    assert emp is not None
    assert emp["joining_date"] == join_date


def test_add_employee_without_explicit_joining_date(conn, monkeypatch):
    """Adding employee without explicit date defaults to today when DEFAULT_JOINING_DATE is unset."""
    monkeypatch.delenv("DEFAULT_JOINING_DATE", raising=False)
    add_employee(conn, "E011", "Manoj Tiwari", "Operations")

    emp = get_employee(conn, "E011")
    assert emp is not None
    assert emp["joining_date"] == datetime.date.today()


def test_add_employee_invalid_joining_date(conn):
    """Invalid joining date format or type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid joining date"):
        add_employee(conn, "E012", "Bad Date", "HR", joining_date="not-a-date")
    with pytest.raises(ValueError, match="Invalid joining date type"):
        add_employee(conn, "E013", "Bad Type", "HR", joining_date=12345)


def test_search_employees_respects_inactive_filter(conn):
    """search_employees respects include_inactive parameter."""
    add_employee(conn, "E001", "Asha Sharma", "Engineering")
    add_employee(conn, "E002", "Asha Verma", "Engineering")
    deactivate_employee(conn, "E002")

    active_only = search_employees(conn, "Asha", include_inactive=False)
    assert len(active_only) == 1
    assert active_only[0]["employee_code"] == "E001"

    both = search_employees(conn, "Asha", include_inactive=True)
    assert len(both) == 2
    codes = {e["employee_code"] for e in both}
    assert codes == {"E001", "E002"}


def test_list_departments(conn):
    """list_departments returns unique sorted list of departments from active employees."""
    add_employee(conn, "E001", "Asha", "Engineering")
    add_employee(conn, "E002", "Ravi", "Sales")
    add_employee(conn, "E003", "Karan", "Engineering")
    add_employee(conn, "E004", "Inactive Dept", "ArchivedDept")
    deactivate_employee(conn, "E004")

    depts = list_departments(conn)
    assert depts == ["Engineering", "Sales"]


def test_get_department_employees(conn):
    """get_department_employees retrieves staff by department, active status, and eligible date."""
    add_employee(conn, "E001", "Asha", "Engineering", joining_date="2026-01-01")
    add_employee(conn, "E002", "Ravi", "Engineering", joining_date="2026-06-01")
    add_employee(conn, "E003", "Karan", "Sales", joining_date="2026-01-01")
    add_employee(conn, "E004", "Departed", "Engineering", joining_date="2026-01-01")
    deactivate_employee(conn, "E004")

    eng_active = get_department_employees(conn, "Engineering", active_only=True)
    assert len(eng_active) == 2
    assert [e["employee_code"] for e in eng_active] == ["E001", "E002"]

    eng_with_inactive = get_department_employees(conn, "Engineering", active_only=False)
    assert len(eng_with_inactive) == 3

    eng_eligible = get_department_employees(
        conn, "Engineering", active_only=True, eligible_as_of=datetime.date(2026, 3, 1)
    )
    assert len(eng_eligible) == 1
    assert eng_eligible[0]["employee_code"] == "E001"

    with pytest.raises(ValueError):
        get_department_employees(conn, "   ")

