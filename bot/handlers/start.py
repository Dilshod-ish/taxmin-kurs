from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.config import settings
from bot.keyboards import currency_keyboard

router = Router(name="start")

WELCOME_TEXT = (
    "Assalomu alaykum! \U0001F44B\n\n"
    "Men O'zbekiston Markaziy banki ma'lumotlari asosida ishlaydigan "
    "valyuta kursi bashoratchi botiman.\n\n"
    "Menga shunchaki valyuta nomini yozing — USD, EUR yoki RUB — "
    "men sizga oxirgi 7 kunlik kurs va keyingi 7 kunlik bashoratni "
    "bitta rasmda yuboraman."
)

HELP_TEXT = (
    "\U0001F4CC Qanday ishlataman:\n\n"
    "Menga shunchaki quyidagi so'zlardan birini yozing:\n"
    f"{', '.join(settings.currencies)}\n\n"
    "Men CBU (Markaziy bank) arxividan ma'lumotni tekshirib, kerak bo'lsa "
    "yuklab olaman, bashorat modelini o'qitaman va oxirgi 7 kun + keyingi "
    "7 kunlik bashoratni bitta rasmda qaytaraman.\n\n"
    "Birinchi so'rov biroz vaqt olishi mumkin (ma'lumot yig'ilayotgani "
    "uchun), keyingi so'rovlar tezroq javob beradi."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=currency_keyboard("fx"))


@router.message(Command("yordam"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
