"""Corporate Excel Report Generator for AttendIQ Attendance Intelligence.

Generates structured, styled multi-tab Excel workbooks (.xlsx) for individual employees
and departments using XlsxWriter.
"""

import datetime
import io
import math
from typing import Any
import xlsxwriter

from src.analysis import get_department_report_data, get_employee_analytics_data


def _is_valid_float(val: Any) -> bool:
    """Check if value is a valid non-NaN, non-infinite number."""
    if val is None:
        return False
    try:
        f = float(val)
        return not (math.isnan(f) or math.isinf(f))
    except (ValueError, TypeError):
        return False


def generate_employee_excel_report(
    conn: Any,
    employee_id: int,
    year: int | None = None,
    month: int | None = None,
) -> bytes:
    """Generate a formatted corporate Excel report (.xlsx) for an individual employee."""
    data = get_employee_analytics_data(conn, employee_id=employee_id, year=year, month=month)
    emp = data["employee"]
    kpis = data["kpis"]
    patterns = data.get("patterns", {})
    records = data.get("records", [])
    monthly_trends = data.get("monthly_trends", [])

    # Sort records ascending by date
    sorted_records = sorted(
        records,
        key=lambda r: (
            datetime.date.fromisoformat(r["attendance_date"])
            if isinstance(r["attendance_date"], str)
            else r["attendance_date"]
        ),
    )

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True, "nan_inf_to_errors": True})

    # Formats
    fmt_title = wb.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": "#1e1b4b",
        "align": "left",
    })
    fmt_subtitle = wb.add_format({
        "font_size": 10,
        "font_color": "#4f46e5",
        "italic": True,
    })
    fmt_header = wb.add_format({
        "bold": True,
        "font_color": "#ffffff",
        "bg_color": "#1e293b",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_section = wb.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": "#0f172a",
        "bg_color": "#f1f5f9",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_label = wb.add_format({
        "bold": True,
        "font_color": "#475569",
        "bg_color": "#f8fafc",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_val = wb.add_format({
        "font_color": "#0f172a",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_val_center = wb.add_format({
        "font_color": "#0f172a",
        "align": "center",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_kpi_num = wb.add_format({
        "bold": True,
        "font_size": 12,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_pct = wb.add_format({
        "bold": True,
        "font_size": 12,
        "align": "center",
        "font_color": "#4f46e5",
        "border": 1,
        "border_color": "#cbd5e1",
        "num_format": "0.00%",
    })

    # Status pills
    fmt_present = wb.add_format({
        "font_color": "#15803d",
        "bg_color": "#dcfce7",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#bbf7d0",
    })
    fmt_absent = wb.add_format({
        "font_color": "#b91c1c",
        "bg_color": "#fee2e2",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#fecaca",
    })
    fmt_leave = wb.add_format({
        "font_color": "#b45309",
        "bg_color": "#fef3c7",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#fde68a",
    })
    fmt_holiday = wb.add_format({
        "font_color": "#4338ca",
        "bg_color": "#e0e7ff",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#c7d2fe",
    })

    # ==========================================
    # Sheet 1: Summary & Performance Analytics
    # ==========================================
    ws_sum = wb.add_worksheet("Summary & Analytics")
    ws_sum.set_column("A:A", 22)
    ws_sum.set_column("B:B", 28)
    ws_sum.set_column("C:C", 20)
    ws_sum.set_column("D:D", 28)
    ws_sum.set_column("E:E", 16)
    ws_sum.set_column("F:F", 16)

    ws_sum.write(0, 0, "AttendIQ · Employee Attendance Statement", fmt_title)
    ws_sum.write(1, 0, f"Reporting Period: {data['reporting_period']} · Generated: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M')}", fmt_subtitle)

    # Employee Details
    ws_sum.merge_range(3, 0, 3, 3, "EMPLOYEE INFORMATION", fmt_section)
    ws_sum.write(4, 0, "Employee Name", fmt_label)
    ws_sum.write(4, 1, emp["employee_name"], fmt_val)
    ws_sum.write(4, 2, "Email Address", fmt_label)
    ws_sum.write(4, 3, emp.get("email") or "Not on file", fmt_val)

    ws_sum.write(5, 0, "Employee Code", fmt_label)
    ws_sum.write(5, 1, emp["employee_code"], fmt_val)
    ws_sum.write(5, 2, "Mobile Number", fmt_label)
    ws_sum.write(5, 3, emp.get("mobile_number") or "Not on file", fmt_val)

    ws_sum.write(6, 0, "Department", fmt_label)
    ws_sum.write(6, 1, emp["department"], fmt_val)
    ws_sum.write(6, 2, "Alternative Phone", fmt_label)
    ws_sum.write(6, 3, emp.get("alt_phone") or "—", fmt_val)

    ws_sum.write(7, 0, "Designation", fmt_label)
    ws_sum.write(7, 1, emp.get("designation") or "Staff Member", fmt_val)
    ws_sum.write(7, 2, "Joining Date", fmt_label)
    ws_sum.write(7, 3, str(emp["joining_date"]), fmt_val)

    # Attendance Metrics
    ws_sum.merge_range(9, 0, 9, 5, "ATTENDANCE METRICS SUMMARY", fmt_section)
    kpi_headers = ["Eligible Days", "Present Days", "Absent Days", "Leave Days", "Holidays", "Attendance Rate"]
    for col_idx, h in enumerate(kpi_headers):
        ws_sum.write(10, col_idx, h, fmt_header)

    ws_sum.write(11, 0, kpis["eligible_days"], fmt_kpi_num)
    ws_sum.write(11, 1, kpis["present"], fmt_kpi_num)
    ws_sum.write(11, 2, kpis["absent"], fmt_kpi_num)
    ws_sum.write(11, 3, kpis["leave"], fmt_kpi_num)
    ws_sum.write(11, 4, kpis["holiday"], fmt_kpi_num)
    if _is_valid_float(kpis.get("attendance_pct")):
        ws_sum.write(11, 5, float(kpis["attendance_pct"]) / 100.0, fmt_pct)
    else:
        ws_sum.write(11, 5, "N/A", fmt_kpi_num)

    # Analysis & Insights
    ws_sum.merge_range(13, 0, 13, 5, "ATTENDANCE PATTERNS & BEHAVIOR INSIGHTS", fmt_section)
    ws_sum.write(14, 0, "Executive Summary", fmt_label)
    ws_sum.merge_range(14, 1, 14, 5, patterns.get("factual_summary", ""), fmt_val)

    ws_sum.write(15, 0, "Consecutive Absences", fmt_label)
    ws_sum.merge_range(15, 1, 15, 5, f"{patterns.get('max_consecutive_absences', 0)} consecutive day(s)", fmt_val)

    ws_sum.write(16, 0, "Top Absent Weekday", fmt_label)
    ws_sum.merge_range(16, 1, 16, 5, patterns.get("top_absent_weekday", "None"), fmt_val)

    ws_sum.write(17, 0, "Period Trend", fmt_label)
    ws_sum.merge_range(17, 1, 17, 5, patterns.get("trend_description", ""), fmt_val)

    # Monthly Breakdown Table
    if monthly_trends:
        ws_sum.merge_range(19, 0, 19, 5, "MONTH-BY-MONTH ATTENDANCE HISTORY", fmt_section)
        m_headers = ["Month", "Present", "Absent", "Leave", "Eligible Days", "Attendance %"]
        for col_idx, h in enumerate(m_headers):
            ws_sum.write(20, col_idx, h, fmt_header)

        for row_idx, m_item in enumerate(monthly_trends, start=21):
            ws_sum.write(row_idx, 0, m_item["label"], fmt_val)
            ws_sum.write(row_idx, 1, m_item["present"], fmt_val_center)
            ws_sum.write(row_idx, 2, m_item["absent"], fmt_val_center)
            ws_sum.write(row_idx, 3, m_item["leave"], fmt_val_center)
            ws_sum.write(row_idx, 4, m_item["eligible_days"], fmt_val_center)
            m_pct = m_item.get("attendance_pct")
            if _is_valid_float(m_pct):
                ws_sum.write(row_idx, 5, float(m_pct) / 100.0, fmt_pct)
            else:
                ws_sum.write(row_idx, 5, "N/A", fmt_val_center)

    # ==========================================
    # Sheet 2: Daily Attendance Log
    # ==========================================
    ws_log = wb.add_worksheet("Daily Attendance Log")
    ws_log.set_column("A:A", 8)
    ws_log.set_column("B:B", 16)
    ws_log.set_column("C:C", 16)
    ws_log.set_column("D:D", 18)
    ws_log.set_column("E:E", 30)

    log_headers = ["#", "Date", "Day of Week", "Attendance Status", "Classification Note"]
    for col_idx, h in enumerate(log_headers):
        ws_log.write(0, col_idx, h, fmt_header)
    ws_log.freeze_panes(1, 0)

    for idx, r in enumerate(sorted_records, start=1):
        ad = r["attendance_date"]
        if isinstance(ad, str):
            ad = datetime.date.fromisoformat(ad)
        st = r["status"]

        if st == "Present":
            st_fmt = fmt_present
        elif st == "Absent":
            st_fmt = fmt_absent
        elif st == "Leave":
            st_fmt = fmt_leave
        else:
            st_fmt = fmt_holiday

        note = "Eligible Working Day" if st in ("Present", "Absent", "Leave") else "Excluded from denominator"

        ws_log.write(idx, 0, idx, fmt_val_center)
        ws_log.write(idx, 1, ad.strftime("%d-%b-%Y"), fmt_val_center)
        ws_log.write(idx, 2, ad.strftime("%A"), fmt_val_center)
        ws_log.write(idx, 3, st, st_fmt)
        ws_log.write(idx, 4, note, fmt_val)

    wb.close()
    return output.getvalue()


def generate_department_excel_report(
    conn: Any,
    department: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> bytes:
    """Generate a multi-tab department attendance audit spreadsheet (.xlsx)."""
    data = get_department_report_data(conn, department=department, year=year, month=month)
    kpis = data["kpis"]
    emp_rows = data["employee_rows"]
    below_75 = data["employees_below_75"]
    dept_summaries = data.get("department_summaries", [])

    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True, "nan_inf_to_errors": True})

    # Common Styles
    fmt_title = wb.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": "#1e1b4b",
        "align": "left",
    })
    fmt_subtitle = wb.add_format({
        "font_size": 10,
        "font_color": "#4f46e5",
        "italic": True,
    })
    fmt_header = wb.add_format({
        "bold": True,
        "font_color": "#ffffff",
        "bg_color": "#1e293b",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_section = wb.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": "#0f172a",
        "bg_color": "#f1f5f9",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_label = wb.add_format({
        "bold": True,
        "font_color": "#475569",
        "bg_color": "#f8fafc",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_val = wb.add_format({
        "font_color": "#0f172a",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_val_center = wb.add_format({
        "font_color": "#0f172a",
        "align": "center",
        "border": 1,
        "border_color": "#e2e8f0",
    })
    fmt_kpi_num = wb.add_format({
        "bold": True,
        "font_size": 12,
        "align": "center",
        "valign": "vcenter",
        "border": 1,
        "border_color": "#cbd5e1",
    })
    fmt_pct = wb.add_format({
        "bold": True,
        "font_size": 11,
        "align": "center",
        "border": 1,
        "border_color": "#cbd5e1",
        "num_format": "0.00%",
    })

    # Warning status styles
    fmt_warn_critical = wb.add_format({
        "font_color": "#991b1b",
        "bg_color": "#fee2e2",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#fecaca",
    })
    fmt_warn_attention = wb.add_format({
        "font_color": "#92400e",
        "bg_color": "#fef3c7",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#fde68a",
    })
    fmt_warn_normal = wb.add_format({
        "font_color": "#166534",
        "bg_color": "#dcfce7",
        "bold": True,
        "align": "center",
        "border": 1,
        "border_color": "#bbf7d0",
    })
    fmt_warn_nodata = wb.add_format({
        "font_color": "#64748b",
        "bg_color": "#f1f5f9",
        "align": "center",
        "border": 1,
        "border_color": "#e2e8f0",
    })

    # ==========================================
    # Sheet 1: Department Overview
    # ==========================================
    ws_sum = wb.add_worksheet("Department Overview")
    ws_sum.set_column("A:A", 22)
    ws_sum.set_column("B:B", 24)
    ws_sum.set_column("C:C", 20)
    ws_sum.set_column("D:D", 20)
    ws_sum.set_column("E:E", 20)
    ws_sum.set_column("F:F", 20)

    ws_sum.write(0, 0, f"AttendIQ · {data['department']} Attendance Report", fmt_title)
    ws_sum.write(1, 0, f"Period: {data['reporting_period']} · Generated: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M')}", fmt_subtitle)

    # Department KPIs
    ws_sum.merge_range(3, 0, 3, 5, "EXECUTIVE SUMMARY", fmt_section)
    kpi_headers = ["Total Employees", "Eligible Days", "Total Present", "Total Absent", "Total Leave", "Department Rate"]
    for col_idx, h in enumerate(kpi_headers):
        ws_sum.write(4, col_idx, h, fmt_header)

    ws_sum.write(5, 0, data["total_employees"], fmt_kpi_num)
    ws_sum.write(5, 1, kpis["eligible_days"], fmt_kpi_num)
    ws_sum.write(5, 2, kpis["present"], fmt_kpi_num)
    ws_sum.write(5, 3, kpis["absent"], fmt_kpi_num)
    ws_sum.write(5, 4, kpis["leave"], fmt_kpi_num)
    if _is_valid_float(kpis.get("attendance_pct")):
        ws_sum.write(5, 5, float(kpis["attendance_pct"]) / 100.0, fmt_pct)
    else:
        ws_sum.write(5, 5, "N/A", fmt_kpi_num)

    # Warning Callout Section (< 75%)
    ws_sum.merge_range(7, 0, 7, 5, "ATTENDANCE ALERTS & EXCEPTIONS (< 75%)", fmt_section)
    if below_75:
        ws_sum.write(8, 0, "Alert Status", fmt_label)
        ws_sum.merge_range(8, 1, 8, 5, f"CRITICAL: {len(below_75)} employee(s) have attendance below 75%", fmt_warn_critical)
        ws_sum.write(9, 0, "Flagged Staff", fmt_label)
        flagged_summary = "; ".join(
            f"{e['employee_name']} ({e['employee_code']}: {e['attendance_pct']:.1f}%)"
            if _is_valid_float(e.get("attendance_pct"))
            else f"{e['employee_name']} ({e['employee_code']}: N/A)"
            for e in below_75
        )
        ws_sum.merge_range(9, 1, 9, 5, flagged_summary, fmt_val)
    else:
        ws_sum.write(8, 0, "Alert Status", fmt_label)
        ws_sum.merge_range(8, 1, 8, 5, "COMPLIANT: All employees satisfied the 75% standard.", fmt_warn_normal)

    # Cross Department Breakdown if available
    if dept_summaries:
        ws_sum.merge_range(11, 0, 11, 5, "DEPARTMENT COMPARISONS", fmt_section)
        d_headers = ["Department", "Present Days", "Absent Days", "Leave Days", "Eligible Days", "Attendance Rate"]
        for col_idx, h in enumerate(d_headers):
            ws_sum.write(12, col_idx, h, fmt_header)

        for row_idx, d_item in enumerate(dept_summaries, start=13):
            ws_sum.write(row_idx, 0, d_item["department"], fmt_val)
            ws_sum.write(row_idx, 1, d_item["present"], fmt_val_center)
            ws_sum.write(row_idx, 2, d_item["absent"], fmt_val_center)
            ws_sum.write(row_idx, 3, d_item["leave"], fmt_val_center)
            ws_sum.write(row_idx, 4, d_item["eligible_days"], fmt_val_center)
            d_pct = d_item.get("attendance_pct")
            if _is_valid_float(d_pct):
                ws_sum.write(row_idx, 5, float(d_pct) / 100.0, fmt_pct)
            else:
                ws_sum.write(row_idx, 5, "N/A", fmt_val_center)

    # ==========================================
    # Sheet 2: Employee Comparison Roster
    # ==========================================
    ws_emp = wb.add_worksheet("Employee Roster")
    ws_emp.set_column("A:A", 6)
    ws_emp.set_column("B:B", 14)
    ws_emp.set_column("C:C", 26)
    ws_emp.set_column("D:D", 20)
    ws_emp.set_column("E:E", 12)
    ws_emp.set_column("F:F", 12)
    ws_emp.set_column("G:G", 12)
    ws_emp.set_column("H:H", 12)
    ws_emp.set_column("I:I", 14)
    ws_emp.set_column("J:J", 16)
    ws_emp.set_column("K:K", 20)

    emp_headers = [
        "#", "Code", "Employee Name", "Department",
        "Present", "Absent", "Leave", "Holiday",
        "Eligible Days", "Attendance %", "Warning Status"
    ]
    for col_idx, h in enumerate(emp_headers):
        ws_emp.write(0, col_idx, h, fmt_header)
    ws_emp.freeze_panes(1, 0)

    for idx, row in enumerate(emp_rows, start=1):
        wl = row["warning_level"]
        if wl == "CRITICAL":
            w_fmt = fmt_warn_critical
        elif wl == "ATTENTION":
            w_fmt = fmt_warn_attention
        elif wl == "NORMAL":
            w_fmt = fmt_warn_normal
        else:
            w_fmt = fmt_warn_nodata

        ws_emp.write(idx, 0, idx, fmt_val_center)
        ws_emp.write(idx, 1, row["employee_code"], fmt_val_center)
        ws_emp.write(idx, 2, row["employee_name"], fmt_val)
        ws_emp.write(idx, 3, row["department"], fmt_val)
        ws_emp.write(idx, 4, row["present"], fmt_val_center)
        ws_emp.write(idx, 5, row["absent"], fmt_val_center)
        ws_emp.write(idx, 6, row["leave"], fmt_val_center)
        ws_emp.write(idx, 7, row["holiday"], fmt_val_center)
        ws_emp.write(idx, 8, row["eligible_days"], fmt_val_center)

        pct = row.get("attendance_pct")
        if _is_valid_float(pct):
            ws_emp.write(idx, 9, float(pct) / 100.0, fmt_pct)
        else:
            ws_emp.write(idx, 9, "N/A", fmt_val_center)

        ws_emp.write(idx, 10, row["warning_label"], w_fmt)

    wb.close()
    return output.getvalue()

