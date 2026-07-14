"""Valyuta kursi bashorati: Prophet vaqt qatori modeli + zaxira (fallback) model.

Har bir valyuta uchun ikkita nomzod model o'qitiladi (mavjud bo'lsa Prophet va
har doim mavjud bo'lgan oddiy trend+hafta kuni modeli), so'nggi 30 kunlik
"holdout" ma'lumotda tekshiriladi (backtest) va eng past MAPE (o'rtacha
foizli xatolik) ko'rsatgan model tanlanadi hamda diskka saqlanadi. Shu
tariqa har bir bashorat qanchalik ishonchli ekani (MAPE) foydalanuvchiga
ham ko'rsatiladi.
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:  # pragma: no cover - prophet ixtiyoriy bog'liqlik
    PROPHET_AVAILABLE = False

HOLDOUT_DAYS = 30
MIN_TRAINING_ROWS = 60


@dataclass(frozen=True)
class ForecastPoint:
    day: date
    value: float
    lower: float
    upper: float


@dataclass(frozen=True)
class ForecastResult:
    currency: str
    model_name: str
    mape: float
    trained_at: str
    points: list[ForecastPoint] = field(default_factory=list)


class SeasonalTrendModel:
    """Prophet mavjud bo'lmaganda ishlatiladigan yengil zaxira model:
    chiziqli trend + hafta kuni bo'yicha o'rtacha og'ish."""

    def __init__(self) -> None:
        self._slope = 0.0
        self._intercept = 0.0
        self._start_ordinal = 0.0
        self._weekday_offsets = np.zeros(7)
        self._residual_std = 0.0

    def fit(self, df: pd.DataFrame) -> "SeasonalTrendModel":
        ordinals = df["ds"].map(date.toordinal).to_numpy(dtype=float)
        self._start_ordinal = float(ordinals.min())
        x = ordinals - self._start_ordinal
        y = df["y"].to_numpy(dtype=float)
        self._slope, self._intercept = np.polyfit(x, y, 1)

        trend = self._slope * x + self._intercept
        residuals = y - trend
        weekdays = df["ds"].map(lambda d: d.weekday()).to_numpy()
        for wd in range(7):
            mask = weekdays == wd
            self._weekday_offsets[wd] = float(residuals[mask].mean()) if mask.any() else 0.0
        self._residual_std = float(residuals.std())
        return self

    def predict(self, future_dates: list[date]) -> pd.DataFrame:
        rows = []
        for d in future_dates:
            x = d.toordinal() - self._start_ordinal
            trend = self._slope * x + self._intercept
            yhat = trend + self._weekday_offsets[d.weekday()]
            rows.append(
                {
                    "ds": d,
                    "yhat": yhat,
                    "yhat_lower": yhat - 1.96 * self._residual_std,
                    "yhat_upper": yhat + 1.96 * self._residual_std,
                }
            )
        return pd.DataFrame(rows)


def _history_to_frame(history: list[tuple[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(history, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"]).dt.date
    return df.sort_values("ds").reset_index(drop=True)


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _fit_prophet(train_df: pd.DataFrame) -> "Prophet":
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        interval_width=0.95,
    )
    prophet_df = train_df.copy()
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
    model.fit(prophet_df)
    return model


def _predict_prophet(model: "Prophet", future_dates: list[date]) -> pd.DataFrame:
    future = pd.DataFrame({"ds": pd.to_datetime(future_dates)})
    forecast = model.predict(future)
    forecast["ds"] = forecast["ds"].dt.date
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def _model_paths(currency: str, models_dir: str) -> tuple[Path, Path]:
    base = Path(models_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{currency}.pkl", base / f"{currency}.meta.json"


def _save_model(
    currency: str,
    kind: str,
    model: object,
    models_dir: str,
    mape: float,
    last_history_date: date,
) -> None:
    model_path, meta_path = _model_paths(currency, models_dir)
    with open(model_path, "wb") as fh:
        pickle.dump({"kind": kind, "model": model}, fh)
    meta_path.write_text(
        json.dumps(
            {
                "kind": kind,
                "mape": mape,
                "last_history_date": last_history_date.isoformat(),
                "trained_at": datetime.utcnow().isoformat(),
            }
        )
    )


def train_model(currency: str, history: list[tuple[str, float]], models_dir: str) -> ForecastResult:
    """Berilgan valyuta uchun eng yaxshi modelni tanlab o'qitadi va saqlaydi."""
    df = _history_to_frame(history)
    if len(df) < MIN_TRAINING_ROWS:
        raise ValueError(
            f"{currency} uchun yetarli tarixiy ma'lumot yo'q "
            f"(kamida {MIN_TRAINING_ROWS} kun kerak, {len(df)} kun mavjud). "
            "Avval 'python -m data.fetch_history' ni ishga tushiring."
        )

    holdout = min(HOLDOUT_DAYS, max(len(df) // 5, 1))
    train_df, test_df = df.iloc[:-holdout], df.iloc[-holdout:]
    test_dates = test_df["ds"].tolist()

    candidates: list[tuple[str, pd.DataFrame]] = []

    if PROPHET_AVAILABLE:
        try:
            prophet_fit = _fit_prophet(train_df)
            prophet_pred = _predict_prophet(prophet_fit, test_dates)
            candidates.append(("prophet", prophet_pred))
        except Exception:
            logger.exception("%s uchun Prophet modelini o'qitishda xatolik yuz berdi", currency)

    fallback_fit = SeasonalTrendModel().fit(train_df)
    fallback_pred = fallback_fit.predict(test_dates)
    candidates.append(("seasonal_trend", fallback_pred))

    scored = [
        (_mape(test_df["y"].to_numpy(), pred["yhat"].to_numpy()), name) for name, pred in candidates
    ]
    scored.sort(key=lambda item: item[0])
    best_mape, best_name = scored[0]

    if best_name == "prophet":
        final_model: object = _fit_prophet(df)
    else:
        final_model = SeasonalTrendModel().fit(df)

    last_history_date = df["ds"].max()
    _save_model(currency, best_name, final_model, models_dir, best_mape, last_history_date)

    return ForecastResult(
        currency=currency,
        model_name=best_name,
        mape=round(best_mape, 2),
        trained_at=datetime.utcnow().isoformat(),
    )


def load_and_forecast(currency: str, days: int, models_dir: str) -> ForecastResult:
    """Oldindan o'qitilgan modelni yuklab, kelgusi `days` kun uchun bashorat qiladi."""
    model_path, meta_path = _model_paths(currency, models_dir)
    if not model_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"{currency} uchun o'qitilgan model topilmadi. "
            "Avval 'python -m forecasting.train' ni ishga tushiring."
        )

    with open(model_path, "rb") as fh:
        payload = pickle.load(fh)
    meta = json.loads(meta_path.read_text())

    last_history_date = date.fromisoformat(meta["last_history_date"])
    future_dates = [last_history_date + timedelta(days=i) for i in range(1, days + 1)]

    kind = payload["kind"]
    model = payload["model"]
    if kind == "prophet":
        forecast_df = _predict_prophet(model, future_dates)
    else:
        forecast_df = model.predict(future_dates)

    points = [
        ForecastPoint(
            day=row.ds,
            value=float(row.yhat),
            lower=float(row.yhat_lower),
            upper=float(row.yhat_upper),
        )
        for row in forecast_df.itertuples(index=False)
    ]

    return ForecastResult(
        currency=currency,
        model_name=kind,
        mape=round(meta["mape"], 2),
        trained_at=meta["trained_at"],
        points=points,
    )
