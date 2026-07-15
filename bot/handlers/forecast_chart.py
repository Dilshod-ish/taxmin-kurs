"""Asosiy handler: foydalanuvchi valyuta kalit so'zini (USD/EUR/RUB) yozganda
— ma'lumot yetarli emasligini tekshirib, kerak bo'lsa CBU'dan yuklab,
modelni (kerak bo'lsa) qayta o'qitib, oxirgi 7 kun + keyingi 7 kunni bitta
rasmda qaytaradi. Alohida oldindan tayyorgarlik bosqichi kerak emas."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import settings
from bot.keyboards import currency_keyboard
from charts.plot import render_combined_chart
from data.fetch_history import backfill
from data.storage import RateStorage
from forecasting.model import forecast_next_days

router = Router(name="forecast_chart")
logger = logging.getLogger(__name__)

HISTORY_DISPLAY_DAYS = 7
FORECAST_DAYS = 7


def _extract_currency(text: str) -> str | None:
    if not text:
        return None
    candidate = text.strip().split()[0].lstrip("/").upper()
    return candidate if candidate in settings.currencies else None


async def _handle_currency(message: Message, currency: str) -> None:
    storage = RateStorage(settings.db_path)
    status = await message.answer(f"⏳ {currency}/UZS uchun ma'lumot tahlil qilinmoqda...")

    try:
        await asyncio.to_thread(
            backfill, [currency], settings.history_window_days, settings.db_path, settings.cbu_base_url
        )
    except Exception:
        logger.exception("%s uchun ma'lumot yuklashda xatolik", currency)

    history = storage.get_history(currency)

    try:
        result = await asyncio.to_thread(
            forecast_next_days, currency, history, FORECAST_DAYS, settings.models_dir
        )
    except ValueError as exc:
        await status.edit_text(str(exc))
        return
    except Exception:
        logger.exception("%s uchun bashorat qilishda xatolik", currency)
        await status.edit_text(
            f"{currency} uchun bashorat qilib bo'lmadi. Birozdan so'ng qayta urinib ko'ring."
        )
        return

    last_n = history[-HISTORY_DISPLAY_DAYS:]
    buffer = render_combined_chart(currency, last_n, result)
    photo = BufferedInputFile(buffer.read(), filename=f"{currency}.png")

    caption = (
        f"{currency}/UZS — so'nggi {len(last_n)} kun va keyingi {FORECAST_DAYS} kun bashorati\n"
        f"Model: {result.model_name} · taxminiy xatolik (MAPE): {result.mape:.2f}%\n\n"
        "⚠️ Statistik bashorat, moliyaviy qaror uchun yagona asos bo'lmasligi kerak."
    )
    await message.answer_photo(photo, caption=caption)
    await status.delete()


@router.message(Command(*[c.lower() for c in settings.currencies]))
async def handle_currency_command(message: Message) -> None:
    currency = _extract_currency(message.text or "")
    if currency:
        await _handle_currency(message, currency)


@router.message(F.text.func(lambda text: _extract_currency(text) is not None))
async def handle_currency_keyword(message: Message) -> None:
    currency = _extract_currency(message.text or "")
    if currency:
        await _handle_currency(message, currency)


@router.message(Command("kurs", "bashorat", "grafik"))
async def handle_legacy_prompt(message: Message) -> None:
    await message.answer(
        "Valyutani tanlang, men oxirgi 7 kun va keyingi 7 kunlik bashoratni bitta rasmda yuboraman:",
        reply_markup=currency_keyboard("fx"),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("fx:"))
async def handle_currency_callback(callback: CallbackQuery) -> None:
    currency = callback.data.split(":")[1]
    await _handle_currency(callback.message, currency)
    await callback.answer()
