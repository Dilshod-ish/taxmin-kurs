from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")

WELCOME_TEXT = (
    "Assalomu alaykum! \U0001F44B\n\n"
    "Men O'zbekiston Markaziy banki ma'lumotlari asosida ishlaydigan "
    "valyuta kursi bashoratchi botiman.\n\n"
    "Buyruqlar:\n"
    "/kurs — joriy kurslarni ko'rish\n"
    "/bashorat USD 7 — 7 kunlik bashorat\n"
    "/grafik USD — tarix va bashorat grafigi\n"
    "/yordam — yordam"
)

HELP_TEXT = (
    "\U0001F4CC Buyruqlar ro'yxati:\n\n"
    "/kurs [valyuta] — joriy kursni ko'rsatadi. Masalan: /kurs USD\n"
    "/bashorat [valyuta] [kunlar] — kelgusi kunlar uchun kurs bashorati. "
    "Masalan: /bashorat EUR 14 (standart: 7 kun, maksimal 30 kun)\n"
    "/grafik [valyuta] — so'nggi 90 kunlik tarix va bashorat grafigini yuboradi\n\n"
    "Bashorat so'nggi 5 yillik tarixiy ma'lumotlar asosida Prophet vaqt qatori "
    "modeli yordamida hisoblanadi va har doim taxminiy xatolik (MAPE) ko'rsatiladi."
)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("yordam"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
