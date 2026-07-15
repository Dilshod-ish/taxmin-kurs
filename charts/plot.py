"""So'nggi kunlar tarixi va bashoratni bitta rasmda chizuvchi modul."""

from __future__ import annotations

import io
from datetime import date

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from forecasting.model import ForecastResult

HIST_COLOR = "#1f4e79"
FORECAST_COLOR = "#c0392b"


def _fmt(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def render_combined_chart(
    currency: str,
    history: list[tuple[str, float]],
    forecast: ForecastResult,
) -> io.BytesIO:
    """`history` — oxirgi N kunlik (sana, kurs) ro'yxati, `forecast` — kelgusi
    kunlar uchun bashorat. Ikkalasi bitta uzluksiz chiziqda ko'rsatiladi."""
    hist_dates = [date.fromisoformat(d) for d, _ in history]
    hist_values = [v for _, v in history]

    fc_dates = [p.day for p in forecast.points]
    fc_values = [p.value for p in forecast.points]
    fc_lower = [p.lower for p in forecast.points]
    fc_upper = [p.upper for p in forecast.points]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)

    ax.plot(
        hist_dates, hist_values, "o-", color=HIST_COLOR, linewidth=2, markersize=5,
        label="So'nggi kunlar (haqiqiy)",
    )
    if hist_dates and fc_dates:
        ax.plot(
            [hist_dates[-1], fc_dates[0]], [hist_values[-1], fc_values[0]], "--",
            color=FORECAST_COLOR, linewidth=1.3, alpha=0.6,
        )
    ax.plot(
        fc_dates, fc_values, "o--", color=FORECAST_COLOR, linewidth=2, markersize=5,
        label="Bashorat",
    )
    ax.fill_between(fc_dates, fc_lower, fc_upper, color=FORECAST_COLOR, alpha=0.12, label="Ishonch oralig'i")

    if hist_dates:
        ax.axvline(hist_dates[-1], color="#8a8a8a", linestyle=":", linewidth=1.2, label="Bugun")

    for d, v in zip(hist_dates, hist_values):
        ax.annotate(_fmt(v), (d, v), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8, color=HIST_COLOR)
    for d, v in zip(fc_dates, fc_values):
        ax.annotate(_fmt(v), (d, v), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8, color=FORECAST_COLOR)

    ax.set_title(f"{currency}/UZS — so'nggi {len(hist_dates)} kun va keyingi {len(fc_dates)} kun bashorati")
    ax.set_ylabel("so'm")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.autofmt_xdate()
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer
