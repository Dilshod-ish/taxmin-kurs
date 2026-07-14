from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings


def currency_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for currency in settings.currencies:
        builder.add(InlineKeyboardButton(text=currency, callback_data=f"{action}:{currency}"))
    builder.adjust(len(settings.currencies))
    return builder.as_markup()
