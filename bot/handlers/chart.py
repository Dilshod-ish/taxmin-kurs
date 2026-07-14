from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import settings
from bot.keyboards import currency_keyboard
from charts.plot import render_chart
from data.storage import RateStorage
from forecasting.model import load_and_forecast

router = Router(name="chart")
storage = RateStorage(settings.db_path)

FORECAST_HORIZON_DAYS = 14


async def _send_chart(message: Message, currency: str) -> None:
    history = storage.get_history(currency)
    if not history:
        await message.answer(f"{currency} uchun tarixiy ma'lumot topilmadi.")
        return

    try:
        forecast = load_and_forecast(currency, FORECAST_HORIZON_DAYS, settings.models_dir)
    except (FileNotFoundError, ValueError):
        forecast = None

    buffer = render_chart(currency, history, forecast)
    photo = BufferedInputFile(buffer.read(), filename=f"{currency}.png")
    await message.answer_photo(photo, caption=f"{currency}/UZS — tarix va bashorat")


@router.message(Command("grafik"))
async def handle_chart(message: Message) -> None:
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer("Valyutani tanlang:", reply_markup=currency_keyboard("chart"))
        return
    currency = args[0].upper()
    if currency not in settings.currencies:
        await message.answer(f"Qo'llab-quvvatlanmaydigan valyuta: {currency}")
        return
    await _send_chart(message, currency)


@router.callback_query(lambda c: c.data and c.data.startswith("chart:"))
async def handle_chart_callback(callback: CallbackQuery) -> None:
    currency = callback.data.split(":")[1]
    await _send_chart(callback.message, currency)
    await callback.answer()
