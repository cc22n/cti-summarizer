"""Tests for Celery summarization worker tasks."""

import pytest
from unittest.mock import MagicMock, patch


class TestSummarizeAlerts:
    def test_empty_id_list_returns_zero_created_and_skipped(self):
        from app.workers.summary_tasks import summarize_alerts

        mock_db = MagicMock()

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            result = summarize_alerts.run([])

        assert result["created"] == 0
        assert result["skipped"] == 0
        mock_db.close.assert_called_once()

    def test_alert_with_existing_summary_is_skipped(self):
        from app.workers.summary_tasks import summarize_alerts

        mock_db = MagicMock()
        # First .all() returns [(42,)] — alert 42 already has a summary
        # Second .all() returns [] — no alerts needed (all skipped)
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [(42,)],
            [],
        ]

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            result = summarize_alerts.run([42])

        assert result["skipped"] == 1
        assert result["created"] == 0

    def test_missing_alert_id_does_not_raise(self):
        from app.workers.summary_tasks import summarize_alerts

        mock_db = MagicMock()
        # No existing summary, then no alert found
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, None]

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            result = summarize_alerts.run([99999])

        assert result["created"] == 0
        assert result["skipped"] == 0

    def test_db_session_closed_on_exception(self):
        from app.workers.summary_tasks import summarize_alerts

        mock_db = MagicMock()
        # First .all() succeeds (no already-summarised alerts).
        # Second .all() raises to simulate a DB error during alert fetch.
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],
            RuntimeError("db error"),
        ]

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with pytest.raises(Exception):
                summarize_alerts.run([1])

        mock_db.close.assert_called_once()


class TestGenerateDailyDigest:
    def test_no_alerts_in_window_returns_skipped(self):
        from app.workers.summary_tasks import generate_daily_digest

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            result = generate_daily_digest.run()

        assert result["status"] == "skipped"
        assert result["reason"] == "no alerts"
        mock_db.close.assert_called_once()

    def test_alerts_found_commits_summary_and_returns_success(self):
        from app.workers.summary_tasks import generate_daily_digest

        mock_db = MagicMock()
        mock_alerts = [MagicMock(), MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_alerts

        mock_summary = MagicMock()

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with patch("app.workers.summary_tasks.run_async", return_value=mock_summary):
                result = generate_daily_digest.run()

        assert result["status"] == "success"
        assert result["alerts_covered"] == 3
        mock_db.add.assert_called_once_with(mock_summary)
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    def test_service_returns_none_reports_failed(self):

        from app.workers.summary_tasks import generate_daily_digest

        mock_db = MagicMock()
        mock_alerts = [MagicMock()]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_alerts

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with patch("app.workers.summary_tasks.run_async", return_value=None):
                result = generate_daily_digest.run()

        assert result["status"] == "failed"


class TestSendWeeklyReportTask:
    def _make_mock_db(self, total: int = 0):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.scalar.return_value = total
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        return mock_db

    def test_calls_send_weekly_report_with_computed_stats(self):
        from app.workers.summary_tasks import send_weekly_report_task

        mock_db = self._make_mock_db(total=0)

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with patch(
                "app.services.email_service.send_weekly_report", return_value=False
            ) as mock_send:
                send_weekly_report_task.run()

        mock_send.assert_called_once()
        stats_arg = mock_send.call_args[0][0]
        assert "total" in stats_arg
        assert "by_severity" in stats_arg
        assert "by_source" in stats_arg

    def test_returns_sent_status_and_total_alerts(self):
        from app.workers.summary_tasks import send_weekly_report_task

        mock_db = self._make_mock_db(total=42)

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with patch(
                "app.services.email_service.send_weekly_report", return_value=True
            ):
                result = send_weekly_report_task.run()

        assert result["sent"] is True
        assert result["total_alerts"] == 42

    def test_db_session_closed_on_exception(self):
        from app.workers.summary_tasks import send_weekly_report_task

        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db failure")

        with patch("app.workers.summary_tasks.SessionLocal", return_value=mock_db):
            with patch.object(
                send_weekly_report_task, "retry", side_effect=RuntimeError("retry")
            ):
                with pytest.raises(Exception):
                    send_weekly_report_task.run()

        mock_db.close.assert_called_once()
