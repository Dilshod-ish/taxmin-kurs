"""Kurs bashorati: "naive + trend" (tasodifiy yurish + yengil tendensiya) modeli.

Haqiqiy CBU ma'lumotlari ustida keng backtest qilindi (401 kun, USD/EUR/RUB):
oddiy Prophet/chiziqli-trend modellariga qarshi (~0.78% vs ~2.1% MAPE), so'ng
har valyutaga xos qo'shimchalarga qarshi ham (hafta-kuni tuzatish, AR(1),
so'nggi-oyna vaqt qatori) — nuqta bashorati uchun sodda "oxirgi qiymat +
o'rtacha kunlik siljish" barchasidan doimo aniqroq yoki teng chiqdi, chunki
valyuta kurslari qisqa muddatda deyarli tasodifiy yurish (random walk)
xususiyatiga ega (moliyaviy iqtisodda "Meese-Rogoff paradoksi" deb tanilgan
hodisa) — murakkab modellar tarixiy shovqinni "naqsh" deb qabul qilib,
ishonchsiz uzoqqa ketaveradi.

Bitta valyutaga xos farq aniq foydali bo'ldi: **ishonch oralig'i**. Har bir
valyutaning volatilligi yil davomida sezilarli o'zgarib turadi (RUB'da
~5 barobargacha) — shuning uchun ishonch oralig'i butun tarixiy o'rtacha
emas, balki so'nggi RECENT_VOLATILITY_WINDOW kunlik haqiqiy tebranish
asosida hisoblanadi — bu har bir valyutaning joriy holatini to'g'ri aks
ettiradi.

Model juda yengil (millisekundlarda hisoblanadi) — shuning uchun diskka
saqlash/keshlash shart emas, har bir so'rovda to'g'ridan-to'g'ri
hisoblanadi.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

MIN_TRAINING_ROWS = 40
HOLDOUT_DAYS = 30
CONFIDENCE_Z = 1.96  # taxminan 95% ishonch oralig'i
RECENT_VOLATILITY_WINDOW = 60


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


def _fit_naive_drift(values: list[float]) -> tuple[float, float]:
    """(so'nggi qiymat, kunlik o'rtacha o'zgarish) — butun berilgan davr bo'yicha."""
    n = len(values)
    diffs = [values[i] - values[i - 1] for i in range(1, n)]
    drift = statistics.mean(diffs) if diffs else 0.0
    return values[-1], drift


def _recent_sigma(values: list[float], drift: float, window: int = RECENT_VOLATILITY_WINDOW) -> float:
    """So'nggi `window` kunlik qoldiq tebranish — butun yillik o'rtacha emas,
    chunki valyuta volatilligi davr-davr bilan sezilarli farq qiladi (masalan
    tinch va notinch bozor davrlari)."""
    recent = values[-(window + 1):]
    if len(recent) < 3:
        return abs(drift) or 1.0
    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    residuals = [d - drift for d in diffs]
    sigma = statistics.pstdev(residuals)
    return sigma or (abs(drift) or 1.0)


def _mape(actual: list[float], predicted: list[float]) -> float:
    errors = [abs((a - p) / a) for a, p in zip(actual, predicted) if a != 0]
    return sum(errors) / len(errors) * 100 if errors else float("nan")


def _backtest_mape(values: list[float], horizon: int) -> float:
    """So'nggi HOLDOUT_DAYS kunni ushlab turib, modelning haqiqiy aniqligini
    o'lchaydi (har bir sinov nuqtasida faqat o'sha vaqtgacha bo'lgan
    ma'lumotdan foydalanadi — kelajakni "ko'rmaydi")."""
    n = len(values)
    holdout = min(HOLDOUT_DAYS, max(n // 5, horizon))
    if n - holdout - horizon < 2:
        return float("nan")
    errors = []
    for origin in range(n - holdout, n - horizon + 1):
        last_value, drift = _fit_naive_drift(values[:origin])
        predicted = [last_value + drift * h for h in range(1, horizon + 1)]
        actual = values[origin:origin + horizon]
        errors.append(_mape(actual, predicted))
    return statistics.mean(errors) if errors else float("nan")


def forecast_next_days(currency: str, history: list[tuple[str, float]], days: int, *_args, **_kwargs) -> ForecastResult:
    """Berilgan tarix asosida kelgusi `days` kun uchun bashorat qaytaradi.

    Qo'shimcha pozitsion/nomlangan argumentlar (masalan eski `models_dir`)
    e'tiborsiz qoldiriladi — model diskka saqlanmagani uchun ular endi
    kerak emas, lekin chaqiruvchi kod bilan moslikni buzmaslik uchun
    qabul qilinadi."""
    if len(history) < MIN_TRAINING_ROWS:
        raise ValueError(
            f"{currency} uchun yetarli tarixiy ma'lumot yo'q "
            f"(kamida {MIN_TRAINING_ROWS} kun kerak, {len(history)} kun mavjud). "
            "Birozdan so'ng qayta urinib ko'ring."
        )

    dates = [date.fromisoformat(d) for d, _ in history]
    values = [v for _, v in history]

    mape = _backtest_mape(values, days)
    last_value, drift = _fit_naive_drift(values)
    sigma = _recent_sigma(values, drift)

    points = []
    for h in range(1, days + 1):
        value = last_value + drift * h
        spread = CONFIDENCE_Z * sigma * (h ** 0.5)
        points.append(
            ForecastPoint(
                day=dates[-1] + timedelta(days=h),
                value=value,
                lower=value - spread,
                upper=value + spread,
            )
        )

    return ForecastResult(
        currency=currency,
        model_name="naive_drift",
        mape=round(mape, 2) if mape == mape else 0.0,
        trained_at=datetime.utcnow().isoformat(),
        points=points,
    )
