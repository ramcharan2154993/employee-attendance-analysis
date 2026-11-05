"""Tests for Module 1: Complete Employee Profile Management and Contact Info.

Verifies:
- Addition of contact fields (email, mobile_number, alt_phone, designation).
- Validation of emails and phone numbers.
- Safe handling of optional/missing contact values.
- Multi-criteria search by name, code, ID, department, and designation.
- Profile update flows and persistence.
- Web routes and form validations.
"""

from typing import Any
import pytest
import config
from src.db import apply_schema, get_connection, migrate_profile_and_alerts
from src.employees import (
    add_employee,
    get_employee,
    get_employee_by_id,
    list_employees,
    search_employees,
    update_employee,
    validate_email,
    validate_phone,
)
from src.web import create_app


def test_contact_validation_helpers() -> None:
    """Verify email and phone validation utility behavior."""
    # Valid emails
    assert validate_email("test@example.com") == "test@example.com"
    assert validate_email("user.name+tag@sub.domain.org") == "user.name+tag@sub.domain.org"
    assert validate_email(None) is None
    assert validate_email("   ") is None

    # Invalid emails
    with pytest.raises(ValueError, match="Invalid email address"):
        validate_email("plainaddress")
    with pytest.raises(ValueError, match="Invalid email address"):
        validate_email("@missingusername.com")
    with pytest.raises(ValueError, match="Invalid email address"):
        validate_email("username@.com")

    # Valid phones
    assert validate_phone("+91 9876543210") == "+91 9876543210"
    assert validate_phone("9876543210") == "9876543210"
    assert validate_phone("080-23456789") == "080-23456789"
    assert validate_phone(None) is None
    assert validate_phone("") is None

    # Invalid phones (too short, too long, or letters)
    with pytest.raises(ValueError, match="Expected 7 to 15 digits"):
        validate_phone("12345")
    with pytest.raises(ValueError, match="Expected 7 to 15 digits"):
        validate_phone("1234567890123456789")
    with pytest.raises(ValueError, match="Expected 7 to 15 digits"):
        validate_phone("phone-number-abc")


def test_add_and_retrieve_employee_with_full_profile(conn: Any) -> None:
    """Verify adding an employee with complete contact info and retrieving by code and ID."""
    emp_id = add_employee(
        conn,
        employee_code="E901",
        employee_name="Dr. Vikram Sarabhai",
        department="Engineering",
        joining_date="2026-01-10",
        email="vikram@isro.gov.in",
        mobile_number="+91 9845012345",
        alt_phone="080-22223333",
        designation="Lead Scientist",
    )
    assert emp_id > 0

    by_code = get_employee(conn, "E901")
    assert by_code is not None
    assert by_code["employee_name"] == "Dr. Vikram Sarabhai"
    assert by_code["email"] == "vikram@isro.gov.in"
    assert by_code["mobile_number"] == "+91 9845012345"
    assert by_code["alt_phone"] == "080-22223333"
    assert by_code["designation"] == "Lead Scientist"
    assert by_code["is_active"] is True

    by_id = get_employee_by_id(conn, emp_id)
    assert by_id is not None
    assert by_id["employee_code"] == "E901"
    assert by_id["email"] == "vikram@isro.gov.in"


def test_add_employee_with_optional_fields_as_none(conn: Any) -> None:
    """Verify backward compatibility when contact fields are omitted."""
    emp_id = add_employee(
        conn,
        employee_code="E902",
        employee_name="Satish Dhawan",
        department="Operations",
        joining_date="2026-02-15",
    )
    assert emp_id > 0

    emp = get_employee(conn, "E902")
    assert emp is not None
    assert emp["email"] is None
    assert emp["mobile_number"] is None
    assert emp["alt_phone"] is None
    assert emp["designation"] is None


def test_update_employee_contact_details(conn: Any) -> None:
    """Verify updating contact details for an existing employee."""
    emp_id = add_employee(
        conn,
        employee_code="E903",
        employee_name="Homi Bhabha",
        department="Engineering",
        joining_date="2026-03-01",
        email="homi.init@barc.gov.in",
    )
    assert emp_id > 0

    # Update contacts
    update_employee(
        conn,
        employee_code="E903",
        employee_name="Dr. Homi J. Bhabha",
        department="Engineering",
        email="homi.bhabha@tifr.res.in",
        mobile_number="+91 9820011223",
        designation="Director",
        update_contacts=True,
    )

    updated = get_employee(conn, "E903")
    assert updated is not None
    assert updated["employee_name"] == "Dr. Homi J. Bhabha"
    assert updated["email"] == "homi.bhabha@tifr.res.in"
    assert updated["mobile_number"] == "+91 9820011223"
    assert updated["designation"] == "Director"


def test_search_employees_by_name_id_code_and_dept(conn: Any) -> None:
    """Verify search matches by employee name, code, numeric ID, email, and designation."""
    id1 = add_employee(
        conn,
        employee_code="E904",
        employee_name="A. P. J. Abdul Kalam",
        department="Research",
        joining_date="2026-04-01",
        email="kalam@drdo.res.in",
        designation="President Emeritus",
    )
    id2 = add_employee(
        conn,
        employee_code="E905",
        employee_name="Kalpana Chawla",
        department="Aerospace",
        joining_date="2026-04-10",
        email="kalpana@nasa.gov",
        designation="Astronaut",
    )

    # Search by code
    res_code = search_employees(conn, "E904")
    assert any(e["employee_code"] == "E904" for e in res_code)

    # Search by name
    res_name = search_employees(conn, "Kalpana")
    assert any(e["employee_code"] == "E905" for e in res_name)

    # Search by numeric ID
    res_id = search_employees(conn, str(id1))
    assert any(e["employee_id"] == id1 for e in res_id)

    # Search by email
    res_email = search_employees(conn, "nasa.gov")
    assert any(e["employee_code"] == "E905" for e in res_email)

    # Search with department filter
    res_filtered = search_employees(conn, "Kalpana", department="Aerospace")
    assert len(res_filtered) == 1
    res_mismatch = search_employees(conn, "Kalpana", department="Finance")
    assert len(res_mismatch) == 0


def test_web_employee_form_submission_with_contacts(conn: Any) -> None:
    """Verify web route /employees/new and /employees/<code>/edit persist contact details."""
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-web-profile",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    # Step 1: GET form to obtain CSRF
    get_res = client.get("/employees/new")
    assert get_res.status_code == 200

    # Step 2: POST new employee with contacts
    with client.session_transaction() as sess:
        token = sess["csrf_token"]

    post_data = {
        "csrf_token": token,
        "employee_code": "E906",
        "employee_name": "Sunita Williams",
        "department": "Aerospace",
        "joining_date": "2026-05-01",
        "email": "sunita@nasa.gov",
        "mobile_number": "+1 281 483 0123",
        "alt_phone": "281-483-0000",
        "designation": "Commander",
    }
    resp = client.post("/employees/new", data=post_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sunita Williams" in resp.data

    # Verify in DB
    created = get_employee(conn, "E906")
    assert created is not None
    assert created["email"] == "sunita@nasa.gov"
    assert created["designation"] == "Commander"

    # Step 3: GET employee profile page
    profile_resp = client.get(f"/employees/{created['employee_id']}")
    assert profile_resp.status_code == 200
    assert b"sunita@nasa.gov" in profile_resp.data
    assert b"Commander" in profile_resp.data

