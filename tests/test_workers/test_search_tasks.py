"""Tests for Celery Elasticsearch forwarding task."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestForwardFunction:
    @pytest.mark.asyncio
    async def test_no_elasticsearch_url_returns_skipped(self):
        from app.workers.search_tasks import _forward

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = ""

        with patch("app.config.settings", mock_settings):
            result = await _forward(2)

        assert result.get("skipped") is True
        assert "ELASTICSEARCH_URL" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_with_url_queries_db_and_calls_bulk_index(self):
        from app.workers.search_tasks import _forward

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = "http://localhost:9200"

        mock_db = MagicMock()
        mock_alerts = [MagicMock(id=1), MagicMock(id=2)]
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value
        ) = mock_alerts

        with patch("app.config.settings", mock_settings):
            with patch("app.database.SessionLocal", return_value=mock_db):
                with patch(
                    "app.services.elasticsearch_service.ensure_index",
                    AsyncMock(return_value=True),
                ):
                    with patch(
                        "app.services.elasticsearch_service.bulk_index_alerts",
                        AsyncMock(return_value=2),
                    ):
                        result = await _forward(2)

        assert result["total"] == 2
        assert result["lookback_hours"] == 2
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_db_session_always_closed(self):
        from app.workers.search_tasks import _forward

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = "http://localhost:9200"

        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("db error")

        with patch("app.config.settings", mock_settings):
            with patch("app.database.SessionLocal", return_value=mock_db):
                with patch(
                    "app.services.elasticsearch_service.ensure_index",
                    AsyncMock(return_value=True),
                ):
                    with pytest.raises(RuntimeError):
                        await _forward(2)

        mock_db.close.assert_called_once()


class TestForwardToElasticsearchTask:
    def test_task_delegates_to_run_async_and_returns_result(self):
        from app.workers.search_tasks import forward_to_elasticsearch_task

        expected = {"indexed": 3, "total": 5, "lookback_hours": 2}

        with patch(
            "app.workers.search_tasks.run_async", return_value=expected
        ) as mock_run_async:
            result = forward_to_elasticsearch_task.run(lookback_hours=2)

        mock_run_async.assert_called_once()
        assert result == expected
