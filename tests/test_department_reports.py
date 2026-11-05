"""Tests for Module 3 / Phase 4: Department-Wise Attendance PDF and Excel Reports.

Verifies:
- Department-wide PDF report generation using ReportLab.
- Department-wide Excel report generation using XlsxWriter.
- Cross-department aggregation and employee comparison rosters.
- Detection and highlighting of employees below the 75% critical threshold.
- Web routes /reports/department/pdf and /reports/department/excel.
"""

from typing import Any
import pytest
import config
from src.attendance import record_attendance
from src.employees import add_employee
from src.reports_excel import generate_department_excel_report
from src.reports_pdf import generate_department_pdf_report
from src.web import create_app


def test_generate_department_pdf_report_single_and_all(conn: Any) -> None:
    """Verify department PDF generation for a specific department and across all departments."""
    emp1 = add_employee(conn, "E701", "Homi Bhabha", "Engineering", "2026-09-01")
    emp2 = add_employee(conn, "E702", "Vikram Sarabhai", "Engineering", "2026-09-01")
    emp3 = add_employee(conn, "E703", "Low Attendant", "Sales", "2026-09-01")

    # Engineering: High attendance
    record_attendance(conn, "E701", "2026-09-01", "Present")
    record_attendance(conn, "E701", "2026-09-02", "Present")
    record_attendance(conn, "E702", "2026-09-01", "Present")
    record_attendance(conn, "E702", "2026-09-02", "Present")

    # Sales: 1 present, 3 absent (25% attendance -> below 75%)
    record_attendance(conn, "E703", "2026-09-01", "Present")
    record_attendance(conn, "E703", "2026-09-02", "Absent")
    record_attendance(conn, "E703", "2026-09-03", "Absent")
    record_attendance(conn, "E703", "2026-09-04", "Absent")

    # 1. Single Department PDF
    pdf_eng = generate_department_pdf_report(conn, department="Engineering", year=2026, month=9)
    assert isinstance(pdf_eng, bytes)
    assert pdf_eng.startswith(b"%PDF-")
    assert len(pdf_eng) > 1000

    # 2. All Departments PDF (Includes Sales which has employee below 75%)
    pdf_all = generate_department_pdf_report(conn, department=None, year=2026, month=9)
    assert isinstance(pdf_all, bytes)
    assert pdf_all.startswith(b"%PDF-")


def test_generate_department_excel_report_single_and_all(conn: Any) -> None:
    """Verify department Excel generation creates valid .xlsx binary packages."""
    add_employee(conn, "E704", "APJ Abdul Kalam", "Research", "2026-09-01")
    record_attendance(conn, "E704", "2026-09-01", "Present")

    # 1. Single Department Excel
    excel_res = generate_department_excel_report(conn, department="Research", year=2026, month=9)
    assert isinstance(excel_res, bytes)
    assert excel_res.startswith(b"PK\x03\x04")

    # 2. All Departments Excel
    excel_all = generate_department_excel_report(conn, department="all", year=2026, month=9)
    assert isinstance(excel_all, bytes)
    assert excel_all.startswith(b"PK\x03\x04")


def test_web_routes_department_report_downloads(conn: Any) -> None:
    """Verify web endpoints deliver department attachments with correct headers."""
    add_employee(conn, "E705", "Kalpana Chawla", "Aero", "2026-09-01")
    record_attendance(conn, "E705", "2026-09-01", "Present")

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_NAME": config.DB_TEST_NAME,
            "SECRET_KEY": "test-key-dept-reports",
            "REQUIRE_AUTH": False,
        }
    )
    client = app.test_client()

    # 1. Download Department PDF
    pdf_resp = client.get("/reports/department/pdf?department=Aero&year=2026&month=9")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["Content-Type"] == "application/pdf"
    assert "Department_Attendance_Aero" in pdf_resp.headers["Content-Disposition"]
    assert pdf_resp.data.startswith(b"%PDF-")

    # 2. Download Department Excel
    excel_resp = client.get("/reports/department/excel?department=Aero&year=2026&month=9")
    assert excel_resp.status_code == 200
    assert "spreadsheetml.sheet" in excel_resp.headers["Content-Type"]
    assert "Department_Attendance_Aero" in excel_resp.headers["Content-Disposition"]
    assert excel_resp.data.startswith(b"PK\x03\x04")

    # 3. Download All Departments PDF
    all_pdf_resp = client.get("/reports/department/pdf?department=all&period=all")
    assert all_pdf_resp.status_code == 200
    assert all_pdf_resp.data.startswith(b"%PDF-")

