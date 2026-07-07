"""Tests for Celery ingestion worker tasks."""

import pytest
from unittest.mock import MagicMock, patch


class TestIngestSource:
    def test_unknown_source_key_returns_error_dict(self):
        from app.workers.ingestion_tasks import ingest_source

        result = ingest_source.run("not_a_real_source")

        assert "error" in result
        assert "not_a_real_source" in result["error"]

    def test_valid_source_key_returns_result_dict(self):
        from app.workers.ingestion_tasks import ingest_source

        mock_result = MagicMock()
        mock_result.source_name = "NVD"
        mock_result.status = "success"
        mock_result.alerts_fetched = 5
        mock_result.alerts_new = 3
        mock_result.error_message = None

        mock_db = MagicMock()

        with patch("app.workers.ingestion_tasks.SessionLocal", return_value=mock_db):
            with patch("app.workers.ingestion_tasks.run_async", return_value=mock_result):
                result = ingest_source.run("nvd")

        assert result["source"] == "NVD"
        assert result["fetched"] == 5
        assert result["new"] == 3
        mock_db.close.assert_called_once()

    def test_db_session_closed_on_exception(self):
        from app.workers.ingestion_tasks import ingest_source

        mock_db = MagicMock()

        with patch("app.workers.ingestion_tasks.SessionLocal", return_value=mock_db):
            with patch("app.workers.ingestion_tasks.run_async", side_effect=RuntimeError("network error")):
                with patch.object(ingest_source, "retry", side_effect=RuntimeError("retry")):
                    with pytest.raises(Exception):
                        ingest_source.run("nvd")

        mock_db.close.assert_called_once()

    def test_result_has_all_expected_keys(self):
        from app.workers.ingestion_tasks import ingest_source

        mock_result = MagicMock()
        mock_result.source_name = "CISA_KEV"
        mock_result.status = "success"
        mock_result.alerts_fetched = 0
        mock_result.alerts_new = 0
        mock_result.error_message = None

        with patch("app.workers.ingestion_tasks.SessionLocal", return_value=MagicMock()):
            with patch("app.workers.ingestion_tasks.run_async", return_value=mock_result):
                result = ingest_source.run("cisa_kev")

        assert set(result.keys()) == {"source", "status", "fetched", "new", "error"}


class TestIngestAllSources:
    def test_dispatches_task_for_each_registered_adapter(self):
        from app.workers.ingestion_tasks import ingest_all_sources, ADAPTERS

        with patch("app.workers.ingestion_tasks.ingest_source") as mock_task:
            mock_task.delay.return_value = MagicMock(id="fake-task-id")
            result = ingest_all_sources.run()

        assert mock_task.delay.call_count == len(ADAPTERS)
        assert set(result.keys()) == set(ADAPTERS.keys())
