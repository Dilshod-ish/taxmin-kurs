import unittest
from datetime import date, timedelta

from forecasting.model import MIN_TRAINING_ROWS, forecast_next_days


def _history(values: list[float], start: date) -> list[tuple[str, float]]:
    return [((start + timedelta(days=i)).isoformat(), v) for i, v in enumerate(values)]


class ForecastNextDaysTests(unittest.TestCase):
    def test_raises_when_not_enough_history(self) -> None:
        history = _history([100.0] * (MIN_TRAINING_ROWS - 1), date(2026, 1, 1))
        with self.assertRaises(ValueError):
            forecast_next_days("USD", history, 7)

    def test_flat_series_forecasts_close_to_last_value(self) -> None:
        history = _history([100.0] * 60, date(2026, 1, 1))
        result = forecast_next_days("USD", history, 7)

        self.assertEqual(result.currency, "USD")
        self.assertEqual(len(result.points), 7)
        for point in result.points:
            self.assertAlmostEqual(point.value, 100.0, places=6)
            self.assertLessEqual(point.lower, point.value)
            self.assertGreaterEqual(point.upper, point.value)

    def test_upward_trend_is_continued_forward(self) -> None:
        values = [100.0 + i for i in range(60)]  # +1 har kuni
        history = _history(values, date(2026, 1, 1))
        result = forecast_next_days("USD", history, 7)

        last_actual = values[-1]
        forecast_values = [p.value for p in result.points]
        # bashorat yo'nalishi davom etishi kerak: har bir keyingi nuqta oldingisidan katta
        self.assertTrue(all(b > a for a, b in zip(forecast_values, forecast_values[1:])))
        self.assertGreater(forecast_values[0], last_actual)

    def test_forecast_dates_are_sequential_after_last_history_day(self) -> None:
        history = _history([100.0] * 60, date(2026, 3, 1))
        result = forecast_next_days("USD", history, 5)

        expected_start = date(2026, 3, 1) + timedelta(days=59) + timedelta(days=1)
        actual_days = [p.day for p in result.points]
        self.assertEqual(actual_days, [expected_start + timedelta(days=i) for i in range(5)])

    def test_confidence_interval_widens_with_horizon(self) -> None:
        values = [100.0 + (i % 5) * 0.7 for i in range(80)]  # ozgina tebranish
        history = _history(values, date(2026, 1, 1))
        result = forecast_next_days("USD", history, 7)

        spreads = [p.upper - p.lower for p in result.points]
        self.assertTrue(all(b >= a for a, b in zip(spreads, spreads[1:])))

    def test_mape_is_non_negative_number(self) -> None:
        values = [100.0 + (i % 5) * 0.7 for i in range(80)]
        history = _history(values, date(2026, 1, 1))
        result = forecast_next_days("USD", history, 7)

        self.assertGreaterEqual(result.mape, 0.0)

    def test_confidence_interval_reflects_recent_volatility_not_full_history(self) -> None:
        # Dastlabki 100 kun juda notinch (katta tebranish), so'nggi 60 kun esa tinch.
        # Ishonch oralig'i so'nggi (tinch) davrni aks ettirishi kerak, butun
        # tarixning (notinch) o'rtachasini emas.
        volatile = [100.0 + (30 if i % 2 == 0 else -30) for i in range(100)]
        calm = [100.0 + (i % 2) * 0.5 for i in range(80)]
        history = _history(volatile + calm, date(2026, 1, 1))
        result = forecast_next_days("USD", history, 1)

        spread = result.points[0].upper - result.points[0].lower
        self.assertLess(spread, 20.0)  # notinch davr sigma'si (~30+) ishlatilganda ancha kengroq bo'lardi


if __name__ == "__main__":
    unittest.main()
