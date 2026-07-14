"""Botni ishga tushiruvchi asosiy fayl.

Ishga tushirish:
    python -m bot.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import chart, forecast, rate, start
from bot.scheduler import setup_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN environment o'zgaruvchisi o'rnatilmagan. .env faylini tekshiring."
        )

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(rate.router)
    dispatcher.include_router(forecast.router)
    dispatcher.include_router(chart.router)

    scheduler = setup_scheduler()
    scheduler.start()

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
