"""Kurs tarixini saqlash uchun sodda SQLite ombori."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS rates (
    currency TEXT NOT NULL,
    rate_date TEXT NOT NULL,
    rate REAL NOT NULL,
    PRIMARY KEY (currency, rate_date)
);
CREATE INDEX IF NOT EXISTS idx_rates_currency_date ON rates (currency, rate_date);
"""


class RateStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_rates(self, currency: str, rows: Iterable[tuple[date, float]]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        with self._connect() as conn:
            cursor = conn.executemany(
                "INSERT INTO rates (currency, rate_date, rate) VALUES (?, ?, ?) "
                "ON CONFLICT(currency, rate_date) DO UPDATE SET rate = excluded.rate",
                [(currency, d.isoformat(), r) for d, r in rows],
            )
            return cursor.rowcount

    def get_existing_dates(self, currency: str) -> set[str]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT rate_date FROM rates WHERE currency = ?", (currency,))
            return {row[0] for row in cursor.fetchall()}

    def get_history(self, currency: str, start: Optional[date] = None) -> list[tuple[str, float]]:
        with self._connect() as conn:
            if start:
                cursor = conn.execute(
                    "SELECT rate_date, rate FROM rates WHERE currency = ? AND rate_date >= ? "
                    "ORDER BY rate_date",
                    (currency, start.isoformat()),
                )
            else:
                cursor = conn.execute(
                    "SELECT rate_date, rate FROM rates WHERE currency = ? ORDER BY rate_date",
                    (currency,),
                )
            return cursor.fetchall()

    def get_latest(self, currency: str) -> Optional[tuple[str, float]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT rate_date, rate FROM rates WHERE currency = ? ORDER BY rate_date DESC LIMIT 1",
                (currency,),
            )
            return cursor.fetchone()
