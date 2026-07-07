"""Tests for the weekly executive report email service."""

from unittest.mock import MagicMock, patch

import pytest


SAMPLE_STATS = {
    "total": 150,
    "by_severity": {"critical": 5, "high": 25, "medium": 40},
    "by_source": {"NVD": 90, "CISA_KEV": 60},
    "period_start": "2026-06-16T00:00:00",
    "period_end": "2026-06-23T00:00:00",
}


class TestBuildHtml:
    def test_contains_total_count(self):
        from app.services.email_service import _build_html

        html = _build_html(SAMPLE_STATS, None)
        assert "150" in html

    def test_includes_non_zero_severity_entries(self):
        from app.services.email_service import _build_html

        html = _build_html(SAMPLE_STATS, None)
        assert "critical" in html.lower()
        assert "high" in html.lower()

    def test_digest_section_rendered_when_provided(self):
        from app.services.email_service import _build_html

        html = _build_html(SAMPLE_STATS, "Ransomware activity increased this week.")
        assert "AI-Generated Summary" in html
        assert "Ransomware" in html

    def test_no_digest_section_when_none(self):
        from app.services.email_service import _build_html

        html = _build_html(SAMPLE_STATS, None)
        assert "AI-Generated Summary" not in html

    def test_html_entities_escaped_in_digest(self):
        from app.services.email_service import _build_html

        html = _build_html(SAMPLE_STATS, "<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestSendWeeklyReport:
    def test_returns_false_when_smtp_not_configured(self):
        from app.services.email_service import send_weekly_report

        mock_settings = MagicMock()
        mock_settings.smtp_host = ""
        mock_settings.smtp_user = ""
        mock_settings.report_email = ""

        with patch("app.config.settings", mock_settings):
            result = send_weekly_report(SAMPLE_STATS)

        assert result is False

    def test_returns_false_on_smtp_error(self):
        from app.services.email_service import send_weekly_report

        mock_settings = MagicMock()
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_pass = ""
        mock_settings.report_email = "report@example.com"

        with patch("app.config.settings", mock_settings):
            with patch(
                "app.services.email_service.smtplib.SMTP",
                side_effect=ConnectionRefusedError("connection refused"),
            ):
                result = send_weekly_report(SAMPLE_STATS)

        assert result is False

    def test_success_calls_sendmail_and_returns_true(self):
        from app.services.email_service import send_weekly_report

        mock_settings = MagicMock()
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "user@example.com"
        mock_settings.smtp_pass = "secret"
        mock_settings.report_email = "report@example.com"

        mock_server = MagicMock()

        with patch("app.config.settings", mock_settings):
            with patch(
                "app.services.email_service.smtplib.SMTP",
                return_value=mock_server,
            ):
                result = send_weekly_report(SAMPLE_STATS, digest_text="Weekly summary.")

        assert result is True
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
