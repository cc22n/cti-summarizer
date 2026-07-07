"""Tests for the threat trend prediction service."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.models.alert import NormalizedAlert, RawAlert
from app.models.source import Source
from app.models.trend_prediction import TrendPrediction
from app.services.prediction_service import (
    FORECAST_DAYS,
    MIN_NONZERO_DAYS,
    SERIES_KEYS,
    _build_series,
    _fetch_daily_counts,
    _fit_prophet,
    _rolling_avg_forecast,
    run_predictions,
)


# ─── helpers ──────────────────────────────────────────────────────────────────


def _seed_source(db) -> Source:
    src = Source(
        name="TEST",
        source_type="api",
        base_url="https://test.example.com",
        polling_interval_minutes=60,
        is_active=True,
    )
    db.add(src)
    db.flush()
    return src


def _seed_alert(db, source_id: int, uid: int, severity: str, days_ago: int) -> None:
    """Insert Source -> RawAlert -> NormalizedAlert with an explicit published_date."""
    raw = RawAlert(
        source_id=source_id,
        external_id=f"PRED-TEST-{uid}",
        raw_data={"test": uid},
    )
    db.add(raw)
    db.flush()
    alert = NormalizedAlert(
        raw_alert_id=raw.id,
        title=f"Prediction Test Alert {uid}",
        severity=severity,
        source_name="TEST",
        published_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db.add(alert)
    db.flush()


def _make_daily_df(days: int, severity: str = "critical", count: int = 2) -> pd.DataFrame:
    today = date.today()
    rows = [
        {"day": str(today - timedelta(days=i)), "severity": severity, "cnt": count}
        for i in range(days)
    ]
    return pd.DataFrame(rows, columns=["day", "severity", "cnt"])


def _make_mock_forecast(start_date: date = None, periods: int = FORECAST_DAYS) -> pd.DataFrame:
    if start_date is None:
        start_date = date.today() + timedelta(days=1)
    dates = pd.date_range(pd.Timestamp(start_date), periods=periods, freq="D")
    return pd.DataFrame({
        "ds": dates,
        "yhat": [3.0] * periods,
        "yhat_lower": [1.0] * periods,
        "yhat_upper": [5.0] * periods,
    })


# ─── _fetch_daily_counts ──────────────────────────────────────────────────────


def test_fetch_daily_counts_empty_db(db):
    df = _fetch_daily_counts(db)
    assert df.empty


def test_fetch_daily_counts_returns_expected_columns_and_groups(db):
    src = _seed_source(db)
    _seed_alert(db, src.id, 1, "critical", days_ago=1)
    _seed_alert(db, src.id, 2, "critical", days_ago=1)
    _seed_alert(db, src.id, 3, "high", days_ago=2)
    db.commit()

    df = _fetch_daily_counts(db)

    assert set(df.columns) == {"day", "severity", "cnt"}
    assert len(df) >= 2
    critical_row = df[df["severity"] == "critical"]
    assert int(critical_row["cnt"].iloc[0]) == 2


# ─── _build_series ────────────────────────────────────────────────────────────


def test_build_series_empty_df_returns_empty():
    df = pd.DataFrame(columns=["day", "severity", "cnt"])
    result = _build_series(df, "critical")
    assert result.empty


def test_build_series_total_sums_all_severities():
    df = pd.DataFrame({
        "day": ["2026-06-01", "2026-06-01", "2026-06-02"],
        "severity": ["critical", "high", "critical"],
        "cnt": [2, 3, 1],
    })
    result = _build_series(df, "total")

    day1 = float(result[result["ds"] == pd.Timestamp("2026-06-01")]["y"].iloc[0])
    day2 = float(result[result["ds"] == pd.Timestamp("2026-06-02")]["y"].iloc[0])
    assert day1 == 5.0
    assert day2 == 1.0


def test_build_series_specific_severity_filters_correctly():
    # Both days have critical data — date range is [Jun 1, Jun 2]
    df = pd.DataFrame({
        "day": ["2026-06-01", "2026-06-02", "2026-06-02"],
        "severity": ["critical", "critical", "high"],
        "cnt": [3, 1, 5],
    })
    result = _build_series(df, "critical")

    assert len(result) == 2
    day1 = float(result[result["ds"] == pd.Timestamp("2026-06-01")]["y"].iloc[0])
    day2 = float(result[result["ds"] == pd.Timestamp("2026-06-02")]["y"].iloc[0])
    assert day1 == 3.0
    assert day2 == 1.0  # critical count on Jun 2, ignoring high=5


def test_build_series_missing_key_fills_all_zeros():
    df = pd.DataFrame({
        "day": ["2026-06-01", "2026-06-02"],
        "severity": ["high", "high"],
        "cnt": [4, 6],
    })
    result = _build_series(df, "critical")
    assert float(result["y"].sum()) == 0.0


def test_build_series_fills_date_gaps_with_zero():
    df = pd.DataFrame({
        "day": ["2026-06-01", "2026-06-03"],
        "severity": ["critical", "critical"],
        "cnt": [2, 4],
    })
    result = _build_series(df, "critical")

    assert len(result) == 3
    gap = float(result[result["ds"] == pd.Timestamp("2026-06-02")]["y"].iloc[0])
    assert gap == 0.0


def test_build_series_ds_is_datetime():
    df = _make_daily_df(5)
    result = _build_series(df, "critical")
    assert pd.api.types.is_datetime64_any_dtype(result["ds"])


def test_build_series_y_is_float():
    df = _make_daily_df(5)
    result = _build_series(df, "critical")
    assert result["y"].dtype == float


# ─── _rolling_avg_forecast ────────────────────────────────────────────────────


def test_rolling_avg_forecast_returns_forecast_days_rows():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=10, freq="D"),
        "y": [float(i + 1) for i in range(10)],
    })
    forecast, model_type = _rolling_avg_forecast(daily)

    assert len(forecast) == FORECAST_DAYS
    assert model_type == "rolling_avg"


def test_rolling_avg_forecast_uses_last_7_values():
    y_vals = [0.0] * 3 + [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=10, freq="D"),
        "y": y_vals,
    })
    forecast, _ = _rolling_avg_forecast(daily)

    expected = sum([1, 2, 3, 4, 5, 6, 7]) / 7
    assert abs(float(forecast["yhat"].iloc[0]) - expected) < 0.01


def test_rolling_avg_forecast_empty_series_returns_zeros():
    daily = pd.DataFrame(columns=["ds", "y"])
    forecast, model_type = _rolling_avg_forecast(daily)

    assert model_type == "rolling_avg"
    assert len(forecast) == FORECAST_DAYS
    assert float(forecast["yhat"].iloc[0]) == 0.0


def test_rolling_avg_forecast_lower_bound_never_negative():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=5, freq="D"),
        "y": [0.2, 0.2, 0.2, 0.2, 0.2],
    })
    forecast, _ = _rolling_avg_forecast(daily)
    assert (forecast["yhat_lower"] >= 0).all()


def test_rolling_avg_forecast_dates_start_after_history():
    last_day = pd.Timestamp("2026-06-10")
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=10, freq="D"),
        "y": [1.0] * 10,
    })
    forecast, _ = _rolling_avg_forecast(daily)
    assert forecast["ds"].min() > last_day


# ─── _fit_prophet ─────────────────────────────────────────────────────────────


def test_fit_prophet_returns_none_if_fewer_than_7_rows():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=5, freq="D"),
        "y": [1.0] * 5,
    })
    assert _fit_prophet(daily) is None


def test_fit_prophet_returns_none_if_too_few_nonzero_days():
    y_vals = [0.0] * (MIN_NONZERO_DAYS - 1) + [1.0] * 8
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-06-01", periods=len(y_vals), freq="D"),
        "y": y_vals,
    })
    assert _fit_prophet(daily) is None


def test_fit_prophet_returns_none_when_prophet_not_installed():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=30, freq="D"),
        "y": [float(i % 5 + 1) for i in range(30)],
    })
    with patch.dict("sys.modules", {"prophet": None}):
        result = _fit_prophet(daily)
    assert result is None


def test_fit_prophet_returns_forecast_and_label_when_data_sufficient():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=30, freq="D"),
        "y": [float(i % 5 + 1) for i in range(30)],
    })
    future_dates = pd.date_range("2026-01-01", periods=44, freq="D")
    mock_forecast = pd.DataFrame({
        "ds": future_dates,
        "yhat": [2.0] * 44,
        "yhat_lower": [1.0] * 44,
        "yhat_upper": [3.0] * 44,
    })
    mock_model = MagicMock()
    mock_model.make_future_dataframe.return_value = pd.DataFrame({"ds": future_dates})
    mock_model.predict.return_value = mock_forecast
    mock_prophet_module = MagicMock()
    mock_prophet_module.Prophet.return_value = mock_model

    with patch.dict("sys.modules", {"prophet": mock_prophet_module}):
        result = _fit_prophet(daily)

    assert result is not None
    forecast, model_type = result
    assert model_type == "prophet"
    assert {"ds", "yhat", "yhat_lower", "yhat_upper"}.issubset(forecast.columns)


def test_fit_prophet_clips_negative_yhat_to_zero():
    daily = pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=30, freq="D"),
        "y": [float(i % 5 + 1) for i in range(30)],
    })
    future_dates = pd.date_range("2026-01-01", periods=44, freq="D")
    mock_forecast = pd.DataFrame({
        "ds": future_dates,
        "yhat": [-5.0] * 44,
        "yhat_lower": [-10.0] * 44,
        "yhat_upper": [-1.0] * 44,
    })
    mock_model = MagicMock()
    mock_model.make_future_dataframe.return_value = pd.DataFrame({"ds": future_dates})
    mock_model.predict.return_value = mock_forecast
    mock_prophet_module = MagicMock()
    mock_prophet_module.Prophet.return_value = mock_model

    with patch.dict("sys.modules", {"prophet": mock_prophet_module}):
        result = _fit_prophet(daily)

    assert result is not None
    forecast, _ = result
    assert (forecast["yhat"] >= 0).all()
    assert (forecast["yhat_lower"] >= 0).all()
    assert (forecast["yhat_upper"] >= 0).all()


# ─── run_predictions ──────────────────────────────────────────────────────────


def test_run_predictions_skips_with_empty_db(db):
    result = run_predictions(db)
    assert result["status"] == "skipped"
    assert result["reason"] == "no_data"


def test_run_predictions_always_returns_run_id(db):
    result = run_predictions(db)
    assert isinstance(result["run_id"], str)
    assert len(result["run_id"]) == 36


def test_run_predictions_stores_rows_for_all_series(db):
    src = _seed_source(db)
    for i in range(5):
        _seed_alert(db, src.id, i, "critical", days_ago=i + 1)
    db.commit()

    result = run_predictions(db)

    assert result["status"] == "success"
    stored_keys = {
        p.series_key for p in db.query(TrendPrediction).all()
    }
    assert stored_keys == set(SERIES_KEYS)


def test_run_predictions_stores_only_future_dates(db):
    src = _seed_source(db)
    for i in range(5):
        _seed_alert(db, src.id, i, "high", days_ago=i + 1)
    db.commit()

    run_predictions(db)

    today = date.today()
    preds = db.query(TrendPrediction).all()
    assert all(p.target_date > today for p in preds)


def test_run_predictions_sparse_data_uses_rolling_avg(db):
    src = _seed_source(db)
    for i in range(3):
        _seed_alert(db, src.id, i, "critical", days_ago=i + 1)
    db.commit()

    run_predictions(db)

    preds = db.query(TrendPrediction).all()
    assert all(p.model_type == "rolling_avg" for p in preds)


def test_run_predictions_all_rows_share_run_id(db):
    src = _seed_source(db)
    for i in range(3):
        _seed_alert(db, src.id, i, "medium", days_ago=i + 1)
    db.commit()

    result = run_predictions(db)
    run_id = result["run_id"]

    preds = db.query(TrendPrediction).all()
    assert all(p.run_id == run_id for p in preds)


def test_run_predictions_predicted_count_non_negative(db):
    src = _seed_source(db)
    for i in range(5):
        _seed_alert(db, src.id, i, "low", days_ago=i + 1)
    db.commit()

    run_predictions(db)

    preds = db.query(TrendPrediction).all()
    assert all(float(p.predicted_count) >= 0 for p in preds)
    assert all(float(p.lower_bound) >= 0 for p in preds)


def test_run_predictions_two_runs_have_different_run_ids(db):
    src = _seed_source(db)
    for i in range(3):
        _seed_alert(db, src.id, i, "info", days_ago=i + 1)
    db.commit()

    r1 = run_predictions(db)
    r2 = run_predictions(db)

    assert r1["run_id"] != r2["run_id"]


def test_run_predictions_uses_prophet_model_type_when_fit_succeeds(db):
    src = _seed_source(db)
    for i in range(5):
        _seed_alert(db, src.id, i, "critical", days_ago=i + 1)
    db.commit()

    mock_fc = _make_mock_forecast()
    with patch("app.services.prediction_service._fit_prophet") as mock_fit:
        mock_fit.return_value = (mock_fc, "prophet")
        result = run_predictions(db)

    assert result["status"] == "success"
    preds = db.query(TrendPrediction).all()
    assert any(p.model_type == "prophet" for p in preds)


def test_run_predictions_rows_count_matches_result(db):
    src = _seed_source(db)
    for i in range(3):
        _seed_alert(db, src.id, i, "critical", days_ago=i + 1)
    db.commit()

    result = run_predictions(db)

    db_count = db.query(TrendPrediction).count()
    assert result["rows"] == db_count
    assert db_count > 0
