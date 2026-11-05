"""Corporate PDF Report Generator for AttendIQ Attendance Intelligence.

Generates professional, printable, multi-page PDF statements for individual employees
and departments using ReportLab, adhering to strict corporate document standards.
"""

import datetime
import io
from typing import Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analysis import get_department_report_data, get_employee_analytics_data


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total page count and adds running header and footer."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header
        self.drawString(54, 755, "AttendIQ · Employee Attendance Statement")
        self.drawRightString(558, 755, "CONFIDENTIAL & OFFICIAL HR RECORD")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(54, 747, 558, 747)

        # Running Footer
        self.line(54, 45, 558, 45)
        gen_time = datetime.datetime.now().strftime("%d-%b-%Y %H:%M")
        self.drawString(54, 34, f"Generated on: {gen_time} · AttendIQ Intelligence System")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_str)

        self.restoreState()


def _get_status_colors(status: str) -> tuple[colors.Color, colors.Color]:
    """Return (text_color, bg_color) for a given status."""
    st = str(status).strip()
    if st == "Present":
        return colors.HexColor("#15803d"), colors.HexColor("#dcfce7")
    if st == "Absent":
        return colors.HexColor("#b91c1c"), colors.HexColor("#fee2e2")
    if st == "Leave":
        return colors.HexColor("#b45309"), colors.HexColor("#fef3c7")
    return colors.HexColor("#4338ca"), colors.HexColor("#e0e7ff")


def generate_employee_pdf_report(
    conn: Any,
    employee_id: int,
    year: int | None = None,
    month: int | None = None,
) -> bytes:
    """Generate a publication-grade individual employee attendance statement PDF."""
    data = get_employee_analytics_data(conn, employee_id=employee_id, year=year, month=month)
    emp = data["employee"]
    kpis = data["kpis"]
    patterns = data.get("patterns", {})
    records = data.get("records", [])

    # Sort records ascending for chronological presentation
    sorted_records = sorted(
        records,
        key=lambda r: (
            datetime.date.fromisoformat(r["attendance_date"])
            if isinstance(r["attendance_date"], str)
            else r["attendance_date"]
        ),
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e1b4b"),
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4f46e5"),
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )

    meta_val_style = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    elements: list[Any] = []

    # 1. Document Header Banner
    elements.append(Paragraph("EMPLOYEE ATTENDANCE STATEMENT", title_style))
    elements.append(
        Paragraph(
            f"REPORTING PERIOD: <b>{data['reporting_period'].upper()}</b> · STATUS: "
            f"<b>{'ACTIVE' if emp['is_active'] else 'INACTIVE'}</b>",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 10))

    # 2. Employee Profile Card (2-column key-value table)
    emp_meta = [
        [
            Paragraph("EMPLOYEE NAME", meta_label_style),
            Paragraph(f"<b>{emp['employee_name']}</b>", meta_val_style),
            Paragraph("EMAIL ADDRESS", meta_label_style),
            Paragraph(emp.get("email") or "Not on file", meta_val_style),
        ],
        [
            Paragraph("EMPLOYEE CODE", meta_label_style),
            Paragraph(f"<b>{emp['employee_code']}</b>", meta_val_style),
            Paragraph("MOBILE NUMBER", meta_label_style),
            Paragraph(emp.get("mobile_number") or "Not on file", meta_val_style),
        ],
        [
            Paragraph("DEPARTMENT", meta_label_style),
            Paragraph(emp["department"], meta_val_style),
            Paragraph("ALTERNATIVE PHONE", meta_label_style),
            Paragraph(emp.get("alt_phone") or "—", meta_val_style),
        ],
        [
            Paragraph("DESIGNATION", meta_label_style),
            Paragraph(emp.get("designation") or "Staff Member", meta_val_style),
            Paragraph("JOINING DATE", meta_label_style),
            Paragraph(str(emp["joining_date"]), meta_val_style),
        ],
    ]

    meta_table = Table(emp_meta, colWidths=[90, 160, 95, 159])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # 3. Attendance Summary KPI Grid
    att_pct_str = f"{kpis['attendance_pct']:.2f}%" if kpis["attendance_pct"] is not None else "N/A"
    abs_pct_str = f"{kpis['absenteeism_pct']:.2f}%" if kpis["absenteeism_pct"] is not None else "N/A"

    kpi_data = [
        [
            Paragraph("<b>Eligible Days</b>", meta_label_style),
            Paragraph("<b>Present</b>", meta_label_style),
            Paragraph("<b>Absent</b>", meta_label_style),
            Paragraph("<b>Approved Leave</b>", meta_label_style),
            Paragraph("<b>Holidays</b>", meta_label_style),
            Paragraph("<b>Attendance %</b>", meta_label_style),
        ],
        [
            Paragraph(f"<font size=13><b>{kpis['eligible_days']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#15803d'><b>{kpis['present']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#b91c1c'><b>{kpis['absent']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#b45309'><b>{kpis['leave']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#4338ca'><b>{kpis['holiday']}</b></font>", meta_val_style),
            Paragraph(f"<font size=14 color='#1e1b4b'><b>{att_pct_str}</b></font>", meta_val_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[84, 84, 84, 84, 84, 84])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))

    # 4. Attendance Analysis & Insights Box
    elements.append(Paragraph("Attendance Pattern & Trend Analysis", section_heading_style))
    analysis_paragraphs = [
        Paragraph(f"• <b>Executive Summary:</b> {patterns.get('factual_summary', '')}", body_style),
        Paragraph(f"• <b>Consecutive Absence Streak:</b> {patterns.get('max_consecutive_absences', 0)} consecutive day(s).", body_style),
        Paragraph(f"• <b>Day-of-Week Distribution:</b> Top absent weekday was {patterns.get('top_absent_weekday', 'None')}.", body_style),
        Paragraph(f"• <b>Trend Insight:</b> {patterns.get('trend_description', '')}", body_style),
    ]

    analysis_table = Table([[p] for p in analysis_paragraphs], colWidths=[504])
    analysis_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(analysis_table)
    elements.append(Spacer(1, 12))

    # 5. Detailed Attendance Table
    elements.append(Paragraph("Detailed Daily Attendance Roster", section_heading_style))

    table_data = [
        [
            Paragraph("<b>#</b>", meta_label_style),
            Paragraph("<b>Date</b>", meta_label_style),
            Paragraph("<b>Day of Week</b>", meta_label_style),
            Paragraph("<b>Attendance Status</b>", meta_label_style),
            Paragraph("<b>Notes / Classification</b>", meta_label_style),
        ]
    ]

    for idx, r in enumerate(sorted_records, 1):
        ad = r["attendance_date"]
        if isinstance(ad, str):
            ad = datetime.date.fromisoformat(ad)
        st = r["status"]
        t_col, b_col = _get_status_colors(st)

        status_p = Paragraph(
            f"<font color='{t_col.hexval()}'><b>{st}</b></font>",
            meta_val_style,
        )

        note = "Eligible Working Day" if st in ("Present", "Absent", "Leave") else "Excluded from denominator"
        table_data.append(
            [
                Paragraph(str(idx), body_style),
                Paragraph(ad.strftime("%d-%b-%Y"), body_style),
                Paragraph(ad.strftime("%A"), body_style),
                status_p,
                Paragraph(note, body_style),
            ]
        )

    if len(table_data) == 1:
        table_data.append([Paragraph("No attendance rows recorded for this period.", body_style), "", "", "", ""])

    daily_table = Table(table_data, colWidths=[30, 110, 110, 110, 144], repeatRows=1)
    daily_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(daily_table)

    # Build the document using NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def generate_department_pdf_report(
    conn: Any,
    department: str | None = None,
    year: int | None = None,
    month: int | None = None,
) -> bytes:
    """Generate a comprehensive department-wide attendance audit report PDF."""
    data = get_department_report_data(conn, department=department, year=year, month=month)
    kpis = data["kpis"]
    emp_rows = data["employee_rows"]
    below_75 = data["employees_below_75"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DeptTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e1b4b"),
    )

    subtitle_style = ParagraphStyle(
        "DeptSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#4f46e5"),
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b"),
    )

    meta_val_style = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    elements: list[Any] = []

    # 1. Header Banner
    elements.append(Paragraph("DEPARTMENT ATTENDANCE AUDIT STATEMENT", title_style))
    elements.append(
        Paragraph(
            f"DEPARTMENT: <b>{data['department'].upper()}</b> · REPORTING SCOPE: <b>{data['reporting_period'].upper()}</b>",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 10))

    # 2. Executive KPI Box
    att_pct_str = f"{kpis['attendance_pct']:.2f}%" if kpis["attendance_pct"] is not None else "N/A"
    abs_pct_str = f"{kpis['absenteeism_pct']:.2f}%" if kpis["absenteeism_pct"] is not None else "N/A"

    kpi_data = [
        [
            Paragraph("<b>Total Staff</b>", meta_label_style),
            Paragraph("<b>Eligible Days</b>", meta_label_style),
            Paragraph("<b>Total Present</b>", meta_label_style),
            Paragraph("<b>Total Absent</b>", meta_label_style),
            Paragraph("<b>Total Leave</b>", meta_label_style),
            Paragraph("<b>Attendance Rate</b>", meta_label_style),
        ],
        [
            Paragraph(f"<font size=13><b>{data['total_employees']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13><b>{kpis['eligible_days']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#15803d'><b>{kpis['present']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#b91c1c'><b>{kpis['absent']}</b></font>", meta_val_style),
            Paragraph(f"<font size=13 color='#b45309'><b>{kpis['leave']}</b></font>", meta_val_style),
            Paragraph(f"<font size=14 color='#1e1b4b'><b>{att_pct_str}</b></font>", meta_val_style),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[88, 88, 89, 89, 89, 99])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 12))

    # 3. Smart Warning Alert Callout Box (< 75%)
    if below_75:
        flagged_names = ", ".join(
            f"<b>{emp['employee_name']}</b> ({emp['employee_code']} · {emp['attendance_pct']:.1f}%)"
            for emp in below_75
        )
        alert_text = (
            f"<font color='#991b1b'><b>ATTENDANCE WARNING (CRITICAL TIER):</b></font> "
            f"The following {len(below_75)} employee(s) fell below the required 75.0% threshold: {flagged_names}. "
            f"HR review and managerial intervention recommended."
        )
        alert_bg = colors.HexColor("#fee2e2")
        alert_border = colors.HexColor("#f87171")
    else:
        alert_text = (
            "<font color='#166534'><b>COMPLIANCE VERIFIED:</b></font> "
            "Zero employees in this department fell below the 75.0% threshold for this reporting period."
        )
        alert_bg = colors.HexColor("#dcfce7")
        alert_border = colors.HexColor("#86efac")

    alert_table = Table([[Paragraph(alert_text, body_style)]], colWidths=[532])
    alert_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), alert_bg),
                ("BOX", (0, 0), (-1, -1), 1, alert_border),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(alert_table)
    elements.append(Spacer(1, 12))

    # 4. Employee Breakdown Table
    elements.append(Paragraph("Employee Attendance Comparison Roster", section_heading_style))

    table_data = [
        [
            Paragraph("<b>#</b>", meta_label_style),
            Paragraph("<b>Code</b>", meta_label_style),
            Paragraph("<b>Employee Name</b>", meta_label_style),
            Paragraph("<b>Department</b>", meta_label_style),
            Paragraph("<b>Present</b>", meta_label_style),
            Paragraph("<b>Absent</b>", meta_label_style),
            Paragraph("<b>Leave</b>", meta_label_style),
            Paragraph("<b>Eligible</b>", meta_label_style),
            Paragraph("<b>Attendance %</b>", meta_label_style),
            Paragraph("<b>Warning Status</b>", meta_label_style),
        ]
    ]

    for idx, row in enumerate(emp_rows, 1):
        pct_val = row["attendance_pct"]
        pct_disp = f"{pct_val:.2f}%" if pct_val is not None else "N/A"

        # Warning Status Styling
        wl = row["warning_level"]
        if wl == "CRITICAL":
            st_color = "#b91c1c"
            st_text = "<b>Below 75%</b>"
        elif wl == "ATTENTION":
            st_color = "#b45309"
            st_text = "<b>75% - 85%</b>"
        elif wl == "NORMAL":
            st_color = "#15803d"
            st_text = "Normal (85%+)"
        else:
            st_color = "#64748b"
            st_text = "No Records"

        table_data.append(
            [
                Paragraph(str(idx), body_style),
                Paragraph(f"<b>{row['employee_code']}</b>", body_style),
                Paragraph(row["employee_name"], body_style),
                Paragraph(row["department"], body_style),
                Paragraph(str(row["present"]), body_style),
                Paragraph(str(row["absent"]), body_style),
                Paragraph(str(row["leave"]), body_style),
                Paragraph(str(row["eligible_days"]), body_style),
                Paragraph(f"<b>{pct_disp}</b>", body_style),
                Paragraph(f"<font color='{st_color}'>{st_text}</font>", body_style),
            ]
        )

    if len(table_data) == 1:
        table_data.append([Paragraph("No employee records found for this scope.", body_style), "", "", "", "", "", "", "", "", ""])

    roster_table = Table(
        table_data,
        colWidths=[24, 46, 110, 80, 42, 42, 40, 44, 56, 78],
        repeatRows=1,
    )
    roster_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("ALIGN", (4, 1), (8, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(roster_table)

    # 5. Department Summary Breakdown (if "All Departments")
    if data["is_all_departments"] and data["department_summaries"]:
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("Cross-Department Attendance Breakdown", section_heading_style))
        d_table_data = [
            [
                Paragraph("<b>Department</b>", meta_label_style),
                Paragraph("<b>Present Days</b>", meta_label_style),
                Paragraph("<b>Absent Days</b>", meta_label_style),
                Paragraph("<b>Leave Days</b>", meta_label_style),
                Paragraph("<b>Total Eligible</b>", meta_label_style),
                Paragraph("<b>Dept Attendance %</b>", meta_label_style),
            ]
        ]
        for d in data["department_summaries"]:
            d_pct = d["attendance_pct"]
            d_pct_str = f"{d_pct:.2f}%" if d_pct is not None else "N/A"
            d_table_data.append(
                [
                    Paragraph(f"<b>{d['department']}</b>", body_style),
                    Paragraph(str(d["present"]), body_style),
                    Paragraph(str(d["absent"]), body_style),
                    Paragraph(str(d["leave"]), body_style),
                    Paragraph(str(d["eligible_days"]), body_style),
                    Paragraph(f"<b>{d_pct_str}</b>", body_style),
                ]
            )
        dept_breakdown_table = Table(d_table_data, colWidths=[120, 80, 80, 80, 80, 92], repeatRows=1)
        dept_breakdown_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(dept_breakdown_table)

    doc.build(elements, canvasmaker=NumberedCanvas)
    return buffer.getvalue()

