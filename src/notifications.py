"""In-Website Notification & Email Integration Module.

Provides:
- Unreviewed attendance warning notification metrics and badge counters.
- Standardized critical warning email notification formatting and SMTP dispatch.
- Graceful degradation (simulated mode when SMTP is unconfigured in development/testing).
- Audit trail for review actions and notification acknowledgment.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Any
from mysql.connector.abstracts import MySQLConnectionAbstract

logger = logging.getLogger(__name__)


def get_notification_summary(conn: MySQLConnectionAbstract) -> dict[str, Any]:
    """Retrieve in-app notification overview: pending review count and latest critical warnings."""
    from src.alerts import count_attendance_alerts, list_attendance_alerts

    unreviewed_total = count_attendance_alerts(conn, is_reviewed=False)
    critical_unreviewed = count_attendance_alerts(conn, warning_level="CRITICAL", is_reviewed=False)
    recent_pending = list_attendance_alerts(conn, is_reviewed=False, limit=5)

    return {
        "unreviewed_count": unreviewed_total,
        "critical_unreviewed": critical_unreviewed,
        "recent_alerts": recent_pending,
    }


def format_alert_email_content(
    employee_name: str,
    employee_code: str,
    period_label: str,
    attendance_pct: float,
    threshold: float,
    present_days: int,
    absent_days: int,
    eligible_days: int,
) -> tuple[str, str]:
    """Format plain text and rich HTML email notifications for critical attendance warnings."""
    subject = f"AttendIQ Alert: Attendance Warning for {employee_name} ({employee_code}) - {period_label}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; background: #f8fafc; padding: 20px; }}
        .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; max-width: 600px; margin: 0 auto; overflow: hidden; }}
        .header {{ background: #dc2626; color: white; padding: 20px 24px; }}
        .header h2 {{ margin: 0; font-size: 20px; }}
        .content {{ padding: 24px; }}
        .stat-box {{ background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 16px 0; border-radius: 4px; }}
        .stat-val {{ font-size: 28px; font-weight: 800; color: #dc2626; }}
        .details {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        .details td {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; }}
        .details td.label {{ color: #64748b; font-weight: 600; width: 40%; }}
        .footer {{ font-size: 12px; color: #94a3b8; padding: 16px 24px; background: #fafbfc; border-top: 1px solid #e2e8f0; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h2>AttendIQ Compliance Alert</h2>
        </div>
        <div class="content">
          <p>Dear HR / Supervisor,</p>
          <p>This is an automated notification from <strong>AttendIQ Employee Attendance Management System</strong>. An employee's attendance for <strong>{period_label}</strong> has fallen below the critical compliance threshold.</p>
          
          <div class="stat-box">
            <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: #991b1b;">Recorded Attendance Rate</div>
            <div class="stat-val">{attendance_pct:.1f}%</div>
            <div style="font-size: 13px; color: #7f1d1d; margin-top: 4px;">Mandatory threshold benchmark: {threshold:.1f}%</div>
          </div>

          <table class="details">
            <tr><td class="label">Employee Name:</td><td><strong>{employee_name}</strong></td></tr>
            <tr><td class="label">Employee Code:</td><td><code>{employee_code}</code></td></tr>
            <tr><td class="label">Reporting Period:</td><td>{period_label}</td></tr>
            <tr><td class="label">Present Days:</td><td><strong style="color: #16a34a;">{present_days}</strong> days</td></tr>
            <tr><td class="label">Absent Days:</td><td><strong style="color: #dc2626;">{absent_days}</strong> days</td></tr>
            <tr><td class="label">Eligible Workdays:</td><td>{eligible_days} days</td></tr>
          </table>

          <p style="margin-top: 20px; font-size: 14px; color: #475569;">
            Please log into the AttendIQ Warning Center to review this case, document supervisor actions, and update the review audit trail.
          </p>
        </div>
        <div class="footer">
          AttendIQ Attendance Intelligence &bull; Automated System Dispatch
        </div>
      </div>
    </body>
    </html>
    """

    return subject, html_content


def dispatch_warning_notification(
    recipient_email: str,
    employee_name: str,
    employee_code: str,
    period_label: str,
    attendance_pct: float,
    threshold: float,
    present_days: int,
    absent_days: int,
    eligible_days: int,
) -> dict[str, Any]:
    """Send or simulate an attendance warning notification email.

    Reads SMTP configuration from environment:
    - SMTP_HOST (e.g. smtp.gmail.com, mail.company.com)
    - SMTP_PORT (default 587)
    - SMTP_USER
    - SMTP_PASSWORD
    - SMTP_FROM (default: attendiq@company.local)
    - SMTP_USE_TLS (default: True)

    If SMTP is not configured or in simulated mode, returns a mock delivery record.
    """
    subject, html_body = format_alert_email_content(
        employee_name=employee_name,
        employee_code=employee_code,
        period_label=period_label,
        attendance_pct=attendance_pct,
        threshold=threshold,
        present_days=present_days,
        absent_days=absent_days,
        eligible_days=eligible_days,
    )

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", "attendiq-alerts@company.local")
    use_tls = os.getenv("SMTP_USE_TLS", "1") == "1"

    if not smtp_host or not recipient_email:
        logger.info(
            "SMTP unconfigured or simulated. Notification for %s (%s) logged safely.",
            employee_name,
            recipient_email,
        )
        return {
            "status": "simulated",
            "delivered": False,
            "recipient": recipient_email,
            "subject": subject,
            "message": "Simulated dispatch (SMTP not configured in local environment).",
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [recipient_email], msg.as_string())

        logger.info("Alert email successfully dispatched to %s", recipient_email)
        return {
            "status": "delivered",
            "delivered": True,
            "recipient": recipient_email,
            "subject": subject,
            "message": "Dispatched via SMTP successfully.",
        }
    except Exception as exc:
        logger.error("Failed to send alert email via SMTP to %s: %s", recipient_email, exc)
        return {
            "status": "failed",
            "delivered": False,
            "recipient": recipient_email,
            "subject": subject,
            "error": str(exc),
        }

