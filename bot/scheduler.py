"""Har kuni bir marta kurslarni yangilab, bashorat modellarini qayta o'qituvchi rejalashtiruvchi."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from data.cbu_client import CbuApiError, CbuClient
from data.storage import RateStorage
from forecasting.model import train_model

logger = logging.getLogger(__name__)


async def refresh_and_retrain() -> None:
    client = CbuClient(base_url=settings.cbu_base_url)
    storage = RateStorage(settings.db_path)

    try:
        today_rates = client.get_current_rates()
    except CbuApiError as exc:
        logger.error("Kunlik kurs yangilanishi muvaffaqiyatsiz tugadi: %s", exc)
        return

    by_currency = {r.currency: r for r in today_rates}
    for currency in settings.currencies:
        rate = by_currency.get(currency)
        if rate is None:
            continue
        storage.upsert_rates(currency, [(rate.rate_date, rate.rate)])

    for currency in settings.currencies:
        history = storage.get_history(currency)
        try:
            result = train_model(currency, history, settings.models_dir)
            logger.info(
                "%s modeli qayta o'qitildi: %s (MAPE=%.2f%%)",
                currency,
                result.model_name,
                result.mape,
            )
        except ValueError as exc:
            logger.warning(str(exc))


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        refresh_and_retrain,
        trigger=CronTrigger(hour=settings.daily_update_hour, minute=settings.daily_update_minute),
        id="daily_refresh_and_retrain",
        replace_existing=True,
    )
    return scheduler
