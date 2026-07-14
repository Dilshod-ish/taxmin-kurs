"""Tarixiy kurs va bashorat grafigini PNG rasm sifatida chizuvchi modul."""

from __future__ import annotations

import io
from datetime import date
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from forecasting.model import ForecastResult


def render_chart(
    currency: str,
    history: list[tuple[str, float]],
    forecast: Optional[ForecastResult] = None,
    history_days: int = 90,
) -> io.BytesIO:
    hist_dates = [date.fromisoformat(d) for d, _ in history][-history_days:]
    hist_values = [v for _, v in history][-history_days:]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.plot(hist_dates, hist_values, label="Tarixiy kurs", color="#1f4e79", linewidth=1.6)

    if forecast and forecast.points:
        fc_dates = [p.day for p in forecast.points]
        fc_values = [p.value for p in forecast.points]
        fc_lower = [p.lower for p in forecast.points]
        fc_upper = [p.upper for p in forecast.points]
        ax.plot(fc_dates, fc_values, label="Bashorat", color="#c0392b", linestyle="--", linewidth=1.8)
        ax.fill_between(fc_dates, fc_lower, fc_upper, color="#c0392b", alpha=0.15, label="Ishonch oralig'i")

    ax.set_title(f"{currency}/UZS kursi va bashorati")
    ax.set_ylabel("so'm")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%y"))
    fig.autofmt_xdate()
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer
