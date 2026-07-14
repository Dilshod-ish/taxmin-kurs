"""CBU arxividan so'nggi N yillik kurs tarixini yuklab, SQLite'ga saqlovchi CLI skript.

Ishga tushirish:
    python -m data.fetch_history --years 5 --currencies USD,EUR,RUB

Skript sana bo'yicha (kunma-kun) "barcha valyutalar" endpointiga so'rov yuboradi,
shuning uchun bitta kun uchun bitta so'rov yetarli bo'ladi. Bazada allaqachon
mavjud bo'lgan kunlar qayta so'ralmaydi — bu skriptni istalgan vaqt xavfsiz
qayta ishga tushirish (davom ettirish) imkonini beradi.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta
from typing import Iterator

from bot.config import settings
from data.cbu_client import CbuApiError, CbuClient
from data.storage import RateStorage

logger = logging.getLogger(__name__)

REQUEST_DELAY_SECONDS = 0.3


def daterange(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def backfill(currencies: list[str], years: int, db_path: str, base_url: str) -> None:
    client = CbuClient(base_url=base_url)
    storage = RateStorage(db_path)
    start = date.today() - timedelta(days=365 * years)
    end = date.today()

    existing_by_currency = {ccy: storage.get_existing_dates(ccy) for ccy in currencies}

    fetched, skipped_days, failed_days = 0, 0, 0
    for day in daterange(start, end):
        day_key = day.isoformat()
        needed = [ccy for ccy in currencies if day_key not in existing_by_currency[ccy]]
        if not needed:
            skipped_days += 1
            continue

        try:
            day_rates = client.get_rates_for_date(day)
        except CbuApiError as exc:
            logger.warning("%s uchun ma'lumot olinmadi: %s", day, exc)
            failed_days += 1
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        by_currency = {r.currency: r for r in day_rates}
        for ccy in needed:
            rate = by_currency.get(ccy)
            if rate is None:
                continue
            storage.upsert_rates(ccy, [(rate.rate_date, rate.rate)])
            fetched += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    logger.info(
        "Yakunlandi: yangi yozuvlar=%s, o'tkazib yuborilgan kunlar=%s, xatolik bergan kunlar=%s",
        fetched,
        skipped_days,
        failed_days,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="CBU tarixiy valyuta kurslarini yuklab olish")
    parser.add_argument("--currencies", default=",".join(settings.currencies))
    parser.add_argument("--years", type=int, default=settings.history_years)
    parser.add_argument("--db-path", default=settings.db_path)
    parser.add_argument("--base-url", default=settings.cbu_base_url)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    currencies = [c.strip().upper() for c in args.currencies.split(",") if c.strip()]
    backfill(currencies, args.years, args.db_path, args.base_url)


if __name__ == "__main__":
    main()
