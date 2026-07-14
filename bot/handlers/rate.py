from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import currency_keyboard
from data.storage import RateStorage

router = Router(name="rate")
storage = RateStorage(settings.db_path)


def _format_rate(currency: str) -> str:
    latest = storage.get_latest(currency)
    if latest is None:
        return f"{currency} uchun ma'lumot topilmadi. Avval tarixiy ma'lumotlarni yuklab oling."
    rate_date, rate = latest
    formatted = f"{rate:,.2f}".replace(",", " ")
    return f"\U0001F4B1 {currency}/UZS: {formatted} so'm ({rate_date} holatiga)"


@router.message(Command("kurs"))
async def handle_rate(message: Message) -> None:
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer("Valyutani tanlang:", reply_markup=currency_keyboard("rate"))
        return
    currency = args[0].upper()
    if currency not in settings.currencies:
        await message.answer(f"Qo'llab-quvvatlanmaydigan valyuta: {currency}")
        return
    await message.answer(_format_rate(currency))


@router.callback_query(lambda c: c.data and c.data.startswith("rate:"))
async def handle_rate_callback(callback: CallbackQuery) -> None:
    currency = callback.data.split(":")[1]
    await callback.message.answer(_format_rate(currency))
    await callback.answer()
