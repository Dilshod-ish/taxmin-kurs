"""CBU arxividan kerakli davr uchun kurs tarixini yuklab, SQLite'ga saqlash.

`backfill()` faqat bazada hali yo'q kunlarni so'raydi, shuning uchun uni
istalgan vaqt (masalan har bir bot so'rovida) qayta chaqirish xavfsiz va
tez — birinchi safar butun oynani (`days`) yuklaydi, keyingi chaqiruvlarda
faqat yangi kunlarni qo'shadi. Tezlik uchun so'rovlar bir nechta ip
(thread) orqali parallel yuboriladi. `time_budget_seconds` — funksiya hech
qachon shu vaqtdan ko'p "osilib qolmasligi" uchun umumiy vaqt chegarasi;
chegaraga yetganda hozirgacha yig'ilgan natija bilan qaytadi.

CLI sifatida ham ishlatish mumkin:
    python -m data.fetch_history --years 5 --currencies USD,EUR,RUB
"""

from __future__ import annotations

import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Iterator

from bot.config import settings
from data.cbu_client import CbuApiError, CbuClient
from data.storage import RateStorage

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 16
DEFAULT_TIME_BUDGET_SECONDS = 60


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
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
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

    def fetch_day(day: date) -> tuple[date, list, str | None]:
        client = CbuClient(base_url=base_url)
        try:
            return day, client.get_rates_for_date(day), None
        except CbuApiError as exc:
            return day, [], str(exc)

    rows_fetched = 0
    completed_days = 0
    error_days = 0
    sample_error: str | None = None

    pool = ThreadPoolExecutor(max_workers=max_workers)
    futures = [pool.submit(fetch_day, day) for day in pending_days]
    timed_out = False
    try:
        for future in as_completed(futures, timeout=time_budget_seconds):
            day, day_rates, error = future.result()
            completed_days += 1
            if error is not None:
                error_days += 1
                if sample_error is None:
                    sample_error = error
                continue
            by_currency = {r.currency: r for r in day_rates}
            for ccy in currencies:
                if day.isoformat() in existing_by_currency[ccy]:
                    continue
                rate = by_currency.get(ccy)
                if rate is None:
                    continue
                storage.upsert_rates(ccy, [(rate.rate_date, rate.rate)])
                rows_fetched += 1
    except TimeoutError:
        timed_out = True
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    summary = (
        f"Yakunlandi: {rows_fetched} ta yangi yozuv, {completed_days}/{len(pending_days)} kun "
        f"tekshirildi, {error_days} kun xato berdi"
    )
    if timed_out:
        summary += f" (vaqt chegarasi {time_budget_seconds:.0f}s ga yetgani uchun to'xtatildi)"
    if sample_error:
        summary += f". Namuna xato: {sample_error}"
    logger.info(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description="CBU tarixiy valyuta kurslarini yuklab olish")
    parser.add_argument("--currencies", default=",".join(settings.currencies))
    parser.add_argument("--years", type=float, default=None, help="Nechchi yillik tarix (masalan 5)")
    parser.add_argument("--days", type=int, default=None, help="Nechchi kunlik tarix (--years o'rniga)")
    parser.add_argument("--db-path", default=settings.db_path)
    parser.add_argument("--base-url", default=settings.cbu_base_url)
    parser.add_argument(
        "--time-budget", type=float, default=None, help="Maksimal ishlash vaqti (soniyada, standart cheklovsiz CLI uchun)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    currencies = [c.strip().upper() for c in args.currencies.split(",") if c.strip()]

    if args.days is not None:
        days = args.days
    elif args.years is not None:
        days = int(args.years * 365)
    else:
        days = int(5 * 365)

    time_budget = args.time_budget if args.time_budget is not None else float("inf")
    backfill(currencies, days, args.db_path, args.base_url, time_budget_seconds=time_budget)


if __name__ == "__main__":
    main()
