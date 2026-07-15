"""Botni ishga tushiruvchi asosiy fayl.

Ishga tushirish:
    python -m bot.main

Alohida "ma'lumot yuklash" yoki "modelni o'qitish" bosqichlari kerak emas —
bot foydalanuvchi valyuta kalit so'zini yozganda buni o'zi bajaradi
(qarang: bot/handlers/forecast_chart.py).
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import forecast_chart, start
from data.storage import RateStorage

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment o'zgaruvchisi o'rnatilmagan. .env faylini tekshiring."
        )

    db_exists = os.path.exists(settings.db_path)
    db_size = os.path.getsize(settings.db_path) if db_exists else 0
    storage = RateStorage(settings.db_path)
    counts = {ccy: len(storage.get_existing_dates(ccy)) for ccy in settings.currencies}
    logger.info(
        "DIAGNOSTIKA: db_path=%s mavjud=%s hajmi=%s bayt, kunlar soni=%s",
        settings.db_path, db_exists, db_size, counts,
    )

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(forecast_chart.router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
