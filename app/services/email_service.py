"""Weekly executive report email service.

Sends an HTML summary of the last 7 days of threat activity via SMTP.
Configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, and REPORT_EMAIL
in .env. If any required setting is missing the function returns silently.
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_weekly_report(stats: dict, digest_text: str | None = None) -> bool:
    """Build and send the weekly executive threat report.

    Args:
        stats: dict with keys total, by_severity, by_source, period_start, period_end
        digest_text: optional LLM-generated digest summary

    Returns:
        True if email was sent, False otherwise.
    """
    from app.config import settings

    required = [settings.smtp_host, settings.smtp_user, settings.report_email]
    if not all(required):
        logger.info(
            "[email] SMTP not configured (SMTP_HOST / SMTP_USER / REPORT_EMAIL missing)"
        )
        return False

    subject = (
        f"CTI Weekly Threat Report - {stats.get('period_end', 'N/A')[:10]}"
    )

    html = _build_html(stats, digest_text)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = settings.report_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        port = settings.smtp_port
        host = settings.smtp_host

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        if settings.smtp_pass:
            server.login(settings.smtp_user, settings.smtp_pass)

        server.sendmail(settings.smtp_user, settings.report_email, msg.as_string())
        server.quit()

        logger.info("[email] Weekly report sent to %s", settings.report_email)
        return True

    except Exception as exc:
        logger.error("[email] Failed to send weekly report: %s", exc)
        return False


def _build_html(stats: dict, digest_text: str | None) -> str:
    """Render the weekly report as an HTML string."""
    total = stats.get("total", 0)
    period_start = stats.get("period_start", "")[:10]
    period_end = stats.get("period_end", "")[:10]

    by_severity = stats.get("by_severity", {})
    by_source = stats.get("by_source", {})

    sev_order = ["critical", "high", "medium", "low", "info"]
    severity_rows = "".join(
        f"<tr><td style='padding:4px 12px;text-transform:capitalize'>{s}</td>"
        f"<td style='padding:4px 12px;text-align:right'>{by_severity.get(s,0)}</td></tr>"
        for s in sev_order
        if by_severity.get(s, 0) > 0
    )

    source_rows = "".join(
        f"<tr><td style='padding:4px 12px'>{src}</td>"
        f"<td style='padding:4px 12px;text-align:right'>{cnt}</td></tr>"
        for src, cnt in sorted(by_source.items(), key=lambda x: -x[1])
    )

    digest_section = ""
    if digest_text:
        escaped = digest_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        digest_section = f"""
        <h3 style='color:#374151;margin-top:24px'>AI-Generated Summary</h3>
        <p style='color:#4b5563;line-height:1.6;background:#f9fafb;padding:12px;border-left:3px solid #3b82f6'>
          {escaped}
        </p>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#111827'>
      <div style='background:#1e3a5f;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0'>
        <h1 style='margin:0;font-size:20px'>CTI Weekly Threat Report</h1>
        <p style='margin:4px 0 0;opacity:0.8;font-size:14px'>{period_start} to {period_end}</p>
      </div>
      <div style='background:#f3f4f6;padding:20px 24px'>

        <h2 style='color:#1f2937;font-size:16px;margin-top:0'>Overview</h2>
        <p style='font-size:28px;font-weight:bold;color:#1e3a5f;margin:0'>{total:,}</p>
        <p style='color:#6b7280;margin:4px 0 16px'>total alerts ingested this week</p>

        <h3 style='color:#374151'>By Severity</h3>
        <table style='width:100%;border-collapse:collapse;background:#fff;border-radius:6px'>
          <thead><tr style='background:#e5e7eb'>
            <th style='padding:6px 12px;text-align:left'>Severity</th>
            <th style='padding:6px 12px;text-align:right'>Count</th>
          </tr></thead>
          <tbody>{severity_rows}</tbody>
        </table>

        <h3 style='color:#374151;margin-top:20px'>By Source</h3>
        <table style='width:100%;border-collapse:collapse;background:#fff;border-radius:6px'>
          <thead><tr style='background:#e5e7eb'>
            <th style='padding:6px 12px;text-align:left'>Source</th>
            <th style='padding:6px 12px;text-align:right'>Count</th>
          </tr></thead>
          <tbody>{source_rows}</tbody>
        </table>

        {digest_section}

        <p style='color:#9ca3af;font-size:11px;margin-top:24px'>
          Generated by CTI Summarizer. This is an automated report.
        </p>
      </div>
    </body>
    </html>
    """
