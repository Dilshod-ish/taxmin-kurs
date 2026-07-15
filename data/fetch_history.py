"""CBU arxividan kerakli davr uchun kurs tarixini yuklab, SQLite'ga saqlash.

`backfill()` faqat bazada hali yo'q kunlarni so'raydi, shuning uchun uni
istalgan vaqt (masalan har bir bot so'rovida) qayta chaqirish xavfsiz va
tez — birinchi safar butun oynani (`days`) yuklaydi, keyingi chaqiruvlarda
faqat yangi kunlarni qo'shadi. Tezlik uchun so'rovlar bir nechta ip
(thread) orqali parallel yuboriladi.

CLI sifatida ham ishlatish mumkin:
    python -m data.fetch_history --years 5 --currencies USD,EUR,RUB
"""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Iterator

from bot.config import settings
from data.cbu_client import CbuApiError, CbuClient
from data.storage import RateStorage

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 8


def daterange(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def backfill(
    currencies: list[str],
    days: int,
    db_path: str,
    base_url: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> None:
    storage = RateStorage(db_path)
    start = date.today() - timedelta(days=days)
    end = date.today()

    existing_by_currency = {ccy: storage.get_existing_dates(ccy) for ccy in currencies}
    pending_days = [
        day
        for day in daterange(start, end)
        if any(day.isoformat() not in existing_by_currency[ccy] for ccy in currencies)
    ]
    if not pending_days:
        logger.info("Barcha kunlar allaqachon bazada mavjud, yuklash shart emas.")
        return

    def fetch_day(day: date) -> tuple[date, list]:
        client = CbuClient(base_url=base_url)
        try:
            return day, client.get_rates_for_date(day)
        except CbuApiError as exc:
            logger.warning("%s uchun ma'lumot olinmadi: %s", day, exc)
            return day, []

    fetched = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_day, day) for day in pending_days]
        for future in as_completed(futures):
            day, day_rates = future.result()
            by_currency = {r.currency: r for r in day_rates}
            for ccy in currencies:
                if day.isoformat() in existing_by_currency[ccy]:
                    continue
                rate = by_currency.get(ccy)
                if rate is None:
                    continue
                storage.upsert_rates(ccy, [(rate.rate_date, rate.rate)])
                fetched += 1

    logger.info("Yakunlandi: %s ta yangi yozuv qo'shildi (%s kun tekshirildi).", fetched, len(pending_days))


def main() -> None:
    parser = argparse.ArgumentParser(description="CBU tarixiy valyuta kurslarini yuklab olish")
    parser.add_argument("--currencies", default=",".join(settings.currencies))
    parser.add_argument("--years", type=float, default=None, help="Nechchi yillik tarix (masalan 5)")
    parser.add_argument("--days", type=int, default=None, help="Nechchi kunlik tarix (--years o'rniga)")
    parser.add_argument("--db-path", default=settings.db_path)
    parser.add_argument("--base-url", default=settings.cbu_base_url)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    currencies = [c.strip().upper() for c in args.currencies.split(",") if c.strip()]

    if args.days is not None:
        days = args.days
    elif args.years is not None:
        days = int(args.years * 365)
    else:
        days = int(5 * 365)

    backfill(currencies, days, args.db_path, args.base_url)


if __name__ == "__main__":
    main()
