import tempfile
import unittest
from datetime import date
from pathlib import Path

from data.storage import RateStorage


class RateStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "test.sqlite3")
        self.storage = RateStorage(self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_upsert_and_get_history(self) -> None:
        self.storage.upsert_rates(
            "USD", [(date(2026, 7, 1), 12500.0), (date(2026, 7, 2), 12550.0)]
        )
        history = self.storage.get_history("USD")
        self.assertEqual(history, [("2026-07-01", 12500.0), ("2026-07-02", 12550.0)])

    def test_upsert_updates_existing(self) -> None:
        self.storage.upsert_rates("USD", [(date(2026, 7, 1), 12500.0)])
        self.storage.upsert_rates("USD", [(date(2026, 7, 1), 12600.0)])
        history = self.storage.get_history("USD")
        self.assertEqual(history, [("2026-07-01", 12600.0)])

    def test_get_latest(self) -> None:
        self.storage.upsert_rates(
            "EUR", [(date(2026, 7, 1), 13500.0), (date(2026, 7, 5), 13650.0)]
        )
        self.assertEqual(self.storage.get_latest("EUR"), ("2026-07-05", 13650.0))

    def test_get_existing_dates(self) -> None:
        self.storage.upsert_rates("RUB", [(date(2026, 7, 1), 145.0)])
        self.assertEqual(self.storage.get_existing_dates("RUB"), {"2026-07-01"})

    def test_get_latest_missing_currency_returns_none(self) -> None:
        self.assertIsNone(self.storage.get_latest("XYZ"))

    def test_get_history_with_start_filter(self) -> None:
        self.storage.upsert_rates(
            "USD",
            [
                (date(2026, 6, 1), 12000.0),
                (date(2026, 7, 1), 12500.0),
                (date(2026, 7, 10), 12600.0),
            ],
        )
        history = self.storage.get_history("USD", start=date(2026, 7, 1))
        self.assertEqual(history, [("2026-07-01", 12500.0), ("2026-07-10", 12600.0)])

    def test_upsert_empty_rows_is_noop(self) -> None:
        self.assertEqual(self.storage.upsert_rates("USD", []), 0)


if __name__ == "__main__":
    unittest.main()
