"""Monthly demand forecasting with an honest backtest.

Why not Prophet / SARIMA with yearly seasonality? Olist has only ~20 reliable months, which is
less than two seasonal cycles, so a yearly seasonal term cannot be estimated. We compare three
simple, defensible models on a hold-out window and keep the one with the lowest MAPE:

    naive        next months = last observed month
    ma3          next months = mean of last 3 months
    holt_damped  exponential smoothing with a damped additive trend (statsmodels)

The naive model is the benchmark: a model that cannot beat it is not worth the complexity.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..warehouse import drilldown, kpis

MODELS = ("naive", "ma3", "holt_damped")
MIN_POINTS = 8


@dataclass
class ForecastResult:
    history: pd.Series  # monthly actuals (index = Timestamp month start)
    best_model: str
    metrics: dict[str, dict[str, float]]  # model -> {"mape":..., "wape":...}
    backtest: pd.DataFrame  # holdout months: actual + one column per model
    forecast: pd.Series  # future months from the best model, refit on all history

    @property
    def mape(self) -> float:
        return self.metrics[self.best_model]["mape"]

    @property
    def naive_mape(self) -> float:
        return self.metrics["naive"]["mape"]


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(actual[mask] - pred[mask]) / np.abs(actual[mask])))


def wape(actual: np.ndarray, pred: np.ndarray) -> float:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    denom = np.abs(actual).sum()
    return float(np.abs(actual - pred).sum() / denom) if denom else float("nan")


def _predict(model: str, train: pd.Series, horizon: int) -> np.ndarray:
    if model == "naive":
        return np.repeat(train.iloc[-1], horizon).astype(float)
    if model == "ma3":
        return np.repeat(train.iloc[-3:].mean(), horizon).astype(float)
    if model == "holt_damped":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(
                train.astype(float),
                trend="add",
                damped_trend=True,
                initialization_method="estimated",
            ).fit()
            return np.asarray(fit.forecast(horizon), dtype=float)
    raise ValueError(f"unknown model {model!r}")


def forecast_series(y: pd.Series, horizon: int = 3, holdout: int = 3) -> ForecastResult:
    """Backtest the models on the last `holdout` months, then forecast `horizon` months ahead."""
    y = y.astype(float)
    if len(y) < max(MIN_POINTS, holdout + 5):
        raise ValueError(f"need at least {max(MIN_POINTS, holdout + 5)} months, got {len(y)}")

    train, test = y.iloc[:-holdout], y.iloc[-holdout:]
    preds = {m: _predict(m, train, holdout) for m in MODELS}
    metrics = {m: {"mape": mape(test.values, p), "wape": wape(test.values, p)} for m, p in preds.items()}
    # lowest MAPE wins; NaN loses; order in MODELS breaks ties (simpler model first)
    ranked = sorted(MODELS, key=lambda m: (np.isnan(metrics[m]["mape"]), metrics[m]["mape"]))
    best = ranked[0]

    backtest = pd.DataFrame({"actual": test.values, **{m: p for m, p in preds.items()}}, index=test.index)
    future_idx = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    forecast = pd.Series(np.maximum(_predict(best, y, horizon), 0.0), index=future_idx)
    return ForecastResult(y, best, metrics, backtest, forecast)


def monthly_series(warehouse: str | Path, category: str | None = None, metric: str = "revenue") -> pd.Series:
    """Complete monthly series over the reliable window (gaps filled with 0)."""
    if metric not in ("revenue", "orders"):
        raise ValueError("metric must be 'revenue' or 'orders'")
    months = drilldown.reliable_months(warehouse)
    if not months:
        return pd.Series(dtype=float)
    start, end = months[0], months[-1]
    if category is None:
        df = kpis.monthly_trend(warehouse, start, end)
    else:
        df = drilldown.category_monthly(warehouse, category, start, end)
    s = pd.Series(df[metric].astype(float).values, index=pd.to_datetime(df["year_month"] + "-01"))
    full = pd.date_range(start + "-01", end + "-01", freq="MS")
    return s.reindex(full, fill_value=0.0)


def forecast_categories(
    warehouse: str | Path, top_n: int = 10, metric: str = "revenue", horizon: int = 3
) -> pd.DataFrame:
    """Backtest + forecast for the top-N categories; one summary row each."""
    rows = []
    for cat in drilldown.categories_by_revenue(warehouse, top=top_n):
        try:
            r = forecast_series(monthly_series(warehouse, cat, metric), horizon=horizon)
        except ValueError:
            continue
        rows.append(
            {
                "category": cat,
                "best_model": r.best_model,
                "mape": round(r.mape, 3),
                "wape": round(r.metrics[r.best_model]["wape"], 3),
                "naive_mape": round(r.naive_mape, 3),
                "last_month_actual": round(float(r.history.iloc[-1]), 2),
                f"next_{horizon}m_forecast": round(float(r.forecast.sum()), 2),
            }
        )
    return pd.DataFrame(rows)
