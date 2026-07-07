"""Tests for Celery prediction worker tasks."""

import pytest
from unittest.mock import MagicMock, patch


class TestRunPredictionTask:
    def test_delegates_to_run_predictions_with_db_session(self):
        from app.workers.prediction_tasks import run_prediction_task

        mock_db = MagicMock()
        mock_result = {"run_id": "test-run-abc", "series_count": 6}

        with patch("app.workers.prediction_tasks.SessionLocal", return_value=mock_db):
            with patch(
                "app.workers.prediction_tasks.run_predictions",
                return_value=mock_result,
            ) as mock_rp:
                result = run_prediction_task.run()

        mock_rp.assert_called_once_with(mock_db)
        assert result == mock_result

    def test_db_session_closed_after_successful_run(self):
        from app.workers.prediction_tasks import run_prediction_task

        mock_db = MagicMock()

        with patch("app.workers.prediction_tasks.SessionLocal", return_value=mock_db):
            with patch(
                "app.workers.prediction_tasks.run_predictions",
                return_value={"run_id": "x"},
            ):
                run_prediction_task.run()

        mock_db.close.assert_called_once()

    def test_db_session_closed_on_exception(self):
        from app.workers.prediction_tasks import run_prediction_task

        mock_db = MagicMock()

        with patch("app.workers.prediction_tasks.SessionLocal", return_value=mock_db):
            with patch(
                "app.workers.prediction_tasks.run_predictions",
                side_effect=RuntimeError("prophet failed"),
            ):
                with patch.object(
                    run_prediction_task, "retry", side_effect=RuntimeError("retry")
                ):
                    with pytest.raises(Exception):
                        run_prediction_task.run()

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
