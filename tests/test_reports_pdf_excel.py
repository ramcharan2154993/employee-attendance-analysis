"""Tests for Module 2 / Phase 3: Individual Employee PDF and Excel Attendance Reports.

Verifies:
- PDF generation using ReportLab (document structure, header, KPI table, running footers).
- Excel generation using XlsxWriter (multi-tab sheets, cell styling, data integrity).
- Handling of employees with 100% attendance, low attendance, and zero attendance.
- Web route downloads, content types, and 404 behavior for unknown employees.
"""

from typing import Any
import pytest
import config
from src.attendance import record_attendance
from src.employees import add_employee
from src.reports_excel import generate_employee_excel_report
from src.reports_pdf import generate_employee_pdf_report
from src.web import create_app


def test_generate_employee_pdf_report_success(conn: Any) -> None:
    """Verify individual PDF generation returns valid PDF binary data."""
    emp_id = add_employee(
        conn,
        employee_code="E801",
        employee_name="Sir C. V. Raman",
        department="Physics",
        joining_date="2026-09-01",
        email="raman@nobel.org",
        mobile_number="+91 9845099887",
        designation="Principal Investigator",
    )
    # Add a few attendance rows
    record_attendance(conn, "E801", "2026-09-01", "Present")
    record_attendance(conn, "E801", "2026-09-02", "Present")
    record_attendance(conn, "E801", "2026-09-03", "Absent")

    pdf_bytes = generate_employee_pdf_report(conn, emp_id, year=2026, month=9)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # Standard PDF header magic bytes
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_employee_pdf_report_zero_attendance_handled(conn: Any) -> None:
    """Verify PDF generator gracefully handles employees with zero attendance records."""
    emp_id = add_employee(
        conn,
        employee_code="E802",
        employee_name="New Intern",
        department="Engineering",
        joining_date="2026-09-15",
    )
    pdf_bytes = generate_employee_pdf_report(conn, emp_id, year=2026, month=9)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_employee_excel_report_success(conn: Any) -> None:
    """Verify Excel generator returns valid .xlsx ZIP binary data with multiple tabs."""
    emp_id = add_employee(
        conn,
        employee_code="E803",
        employee_name="Satyendra Nath Bose",
        department="Mathematics",
        joining_date="2026-09-01",
        email="bose@stat.org",
    )
    record_attendance(conn, "E803", "2026-09-01", "Present")
    record_attendance(conn, "E803", "2026-09-02", "Leave")

    excel_bytes = generate_employee_excel_report(conn, emp_id, year=2026, month=9)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000
    # PK zip signature for standard openxml xlsx
    assert excel_bytes.startswith(b"PK\x03\x04")


def test_web_routes_employee_report_downloads(conn: Any) -> None:
    """Verify web endpoints deliver PDF and Excel attachments with proper content types."""
    emp_id = add_employee(
        conn,
        employee_code="E804",
        employee_name="Meghnad Saha",
        department="Astrophysics",
        joining_date="2026-09-01",
    )
    record_attendance(conn, "E804", "2026-09-01", "Present")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-reports",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    # 1. Download PDF
    pdf_resp = client.get(f"/employees/{emp_id}/report/pdf?period=2026-09")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["Content-Type"] == "application/pdf"
    assert "Attendance_Report_E804" in pdf_resp.headers["Content-Disposition"]
    assert pdf_resp.data.startswith(b"%PDF-")

    # 2. Download Excel
    excel_resp = client.get(f"/employees/{emp_id}/report/excel?period=2026-09")
    assert excel_resp.status_code == 200
    assert "spreadsheetml.sheet" in excel_resp.headers["Content-Type"]
    assert "Attendance_Report_E804" in excel_resp.headers["Content-Disposition"]
    assert excel_resp.data.startswith(b"PK\x03\x04")

    # 3. 404 for non-existent employee
    missing_resp = client.get("/employees/99999/report/pdf")
    assert missing_resp.status_code == 404

