"""Threat trend prediction service using Prophet.

Trains one Prophet model per severity series on historical alert counts,
then stores 14-day forecasts in trend_predictions.

Windows fallback: if 'prophet' fails to install (Stan/C++ compile error),
replace with 'neuralprophet' (pure PyTorch, same API):
    pip install neuralprophet --break-system-packages
    change: from prophet import Prophet
    to:     from neuralprophet import NeuralProphet as Prophet
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import NormalizedAlert
from app.models.trend_prediction import TrendPrediction

logger = logging.getLogger(__name__)

SERIES_KEYS = ["critical", "high", "medium", "low", "info", "total"]

# These constants are read from settings so they can be tuned via .env.
# They remain importable by name for test compatibility.
FORECAST_DAYS: int = settings.forecast_days
MIN_NONZERO_DAYS: int = settings.min_nonzero_days
LOOKBACK_DAYS: int = settings.lookback_days


def _fetch_daily_counts(db: Session):
    """Return rows of (day, severity, cnt) for the last lookback_days."""
    import pandas as pd

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    rows = (
        db.query(
            func.date(
                func.coalesce(
                    NormalizedAlert.published_date,
                    NormalizedAlert.normalized_at,
                )
            ).label("day"),
            NormalizedAlert.severity,
            func.count(NormalizedAlert.id).label("cnt"),
        )
        .filter(
            func.coalesce(
                NormalizedAlert.published_date,
                NormalizedAlert.normalized_at,
            )
            >= cutoff
        )
        .group_by("day", NormalizedAlert.severity)
        .order_by("day")
        .all()
    )

    if not rows:
        return pd.DataFrame(columns=["day", "severity", "cnt"])
    return pd.DataFrame(rows, columns=["day", "severity", "cnt"])


def _build_series(df, key: str):
    """Build a complete daily time series DataFrame for Prophet.

    Returns DataFrame with columns: ds (datetime64), y (float).
    Missing dates are filled with 0.
    """
    import pandas as pd

    if df.empty:
        return pd.DataFrame(columns=["ds", "y"])

    if key == "total":
        daily = df.groupby("day")["cnt"].sum().reset_index()
        daily.columns = ["ds", "y"]
    else:
        subset = df[df["severity"] == key].copy()
        if subset.empty:
            all_days = df["day"].unique()
            daily = pd.DataFrame({"ds": all_days, "y": 0.0})
        else:
            daily = subset[["day", "cnt"]].copy()
            daily.columns = ["ds", "y"]

    daily["ds"] = pd.to_datetime(daily["ds"])
    daily["y"] = daily["y"].astype(float)

    # Collapse any duplicate dates before reindexing
    daily = daily.groupby("ds", as_index=False)["y"].sum()

    if not daily.empty:
        date_range = pd.date_range(daily["ds"].min(), daily["ds"].max(), freq="D")
        daily = (
            daily.set_index("ds")
            .reindex(date_range)
            .fillna(0.0)
            .reset_index()
            .rename(columns={"index": "ds"})
        )

    return daily


def _fit_prophet(daily) -> tuple | None:
    """Fit Prophet and return (forecast_df, 'prophet').

    Returns None if data is insufficient (use rolling avg fallback).
    forecast_df has columns: ds, yhat, yhat_lower, yhat_upper.
    """
    import logging as _logging

    nonzero_count = int((daily["y"] > 0).sum())
    if len(daily) < 7 or nonzero_count < MIN_NONZERO_DAYS:
        logger.debug("Insufficient data (%d rows, %d nonzero)", len(daily), nonzero_count)
        return None

    try:
        from prophet import Prophet

        # Suppress Stan / Prophet verbose logging
        _logging.getLogger("prophet").setLevel(_logging.WARNING)
        _logging.getLogger("cmdstanpy").setLevel(_logging.WARNING)

        m = Prophet(
            interval_width=0.80,
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        m.fit(daily)
        future = m.make_future_dataframe(periods=FORECAST_DAYS, freq="D")
        forecast = m.predict(future)

        forecast["yhat"] = forecast["yhat"].clip(lower=0.0)
        forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0.0)
        forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0.0)

        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]], "prophet"

    except Exception as exc:
        logger.warning(
            "[prediction] Prophet unavailable (%s) — falling back to rolling avg", exc
        )
        return None


def _rolling_avg_forecast(daily):
    """Fallback: flat 7-day rolling average for sparse series."""
    import pandas as pd

    avg = float(daily["y"].tail(7).mean()) if not daily.empty else 0.0
    avg = max(avg, 0.0)

    last_date = daily["ds"].max() if not daily.empty else pd.Timestamp.now()
    future_dates = pd.date_range(
        last_date + timedelta(days=1), periods=FORECAST_DAYS, freq="D"
    )
    forecast = pd.DataFrame({
        "ds": future_dates,
        "yhat": avg,
        "yhat_lower": max(0.0, avg * 0.5),
        "yhat_upper": avg * 1.5,
    })
    return forecast, "rolling_avg"


def run_predictions(db: Session) -> dict:
    """Main entry: fetch history, fit models, store predictions.

    Returns a summary dict with run_id, status, and row count.
    """
    run_id = str(uuid.uuid4())
    raw_df = _fetch_daily_counts(db)

    if raw_df.empty:
        logger.warning("[prediction] No historical data - skipping")
        return {"run_id": run_id, "status": "skipped", "reason": "no_data"}

    days_range = raw_df["day"].nunique()
    training_days = int(days_range)
    today = date.today()
    rows_stored = 0

    for key in SERIES_KEYS:
        daily = _build_series(raw_df, key)
        result = _fit_prophet(daily)

        if result is None:
            forecast, model_type = _rolling_avg_forecast(daily)
        else:
            forecast, model_type = result

        # Keep only future dates (after today)
        future_only = forecast[forecast["ds"].dt.date > today].copy()

        # Anomaly threshold: historical mean + 2*std so that a spike in the
        # forecast is measured against the baseline, not against other forecast
        # values (using forecast values produces near-zero std on stable series,
        # causing false-positive anomaly flags on almost every point).
        hist_vals = daily["y"].dropna()
        if len(hist_vals) > 1:
            mean_y = float(hist_vals.mean())
            std_y = float(hist_vals.std())
            anomaly_threshold = mean_y + 2 * std_y
        else:
            anomaly_threshold = float("inf")

        for _, row in future_only.iterrows():
            yhat_val = float(row["yhat"])
            pred = TrendPrediction(
                run_id=run_id,
                series_key=key,
                target_date=row["ds"].date(),
                predicted_count=Decimal(str(round(yhat_val, 2))),
                lower_bound=Decimal(str(round(float(row["yhat_lower"]), 2))),
                upper_bound=Decimal(str(round(float(row["yhat_upper"]), 2))),
                model_type=model_type,
                training_days=training_days,
                is_anomaly=yhat_val > anomaly_threshold,
            )
            db.add(pred)
            rows_stored += 1

    db.commit()
    logger.info(
        "[prediction] run_id=%s model=prophet rows=%d training_days=%d",
        run_id,
        rows_stored,
        training_days,
    )
    return {
        "run_id": run_id,
        "status": "success",
        "rows": rows_stored,
        "training_days": training_days,
    }
