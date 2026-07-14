from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.keyboards import currency_keyboard
from forecasting.model import load_and_forecast

router = Router(name="forecast")

DEFAULT_DAYS = 7


def _format_forecast(currency: str, days: int) -> str:
    days = max(1, min(days, settings.max_forecast_days))
    try:
        result = load_and_forecast(currency, days, settings.models_dir)
    except (FileNotFoundError, ValueError) as exc:
        return str(exc)

    lines = [
        f"\U0001F4C8 {currency}/UZS uchun {days} kunlik bashorat",
        f"(model: {result.model_name}, taxminiy xatolik MAPE: {result.mape:.2f}%)",
        "",
    ]
    for point in result.points:
        value = f"{point.value:,.0f}".replace(",", " ")
        lower = f"{point.lower:,.0f}".replace(",", " ")
        upper = f"{point.upper:,.0f}".replace(",", " ")
        lines.append(f"{point.day.strftime('%d.%m.%Y')}: {value} so'm ({lower}–{upper})")
    lines.append(
        "\n⚠️ Bu bashorat statistik model asosida hisoblangan, "
        "moliyaviy qaror uchun yagona asos bo'lmasligi kerak."
    )
    return "\n".join(lines)


@router.message(Command("bashorat"))
async def handle_forecast(message: Message) -> None:
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer("Valyutani tanlang:", reply_markup=currency_keyboard("forecast"))
        return
    currency = args[0].upper()
    if currency not in settings.currencies:
        await message.answer(f"Qo'llab-quvvatlanmaydigan valyuta: {currency}")
        return
    days = DEFAULT_DAYS
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
    await message.answer(_format_forecast(currency, days))


@router.callback_query(lambda c: c.data and c.data.startswith("forecast:"))
async def handle_forecast_callback(callback: CallbackQuery) -> None:
    currency = callback.data.split(":")[1]
    await callback.message.answer(_format_forecast(currency, DEFAULT_DAYS))
    await callback.answer()
