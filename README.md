# Taxmin Kurs — O'zbek so'miga nisbatan valyuta kursi bashoratchi Telegram bot

Bu bot O'zbekiston Respublikasi Markaziy banki (CBU) rasmiy JSON arxividan
so'nggi 5 yillik tarixiy kurslarni yig'ib, shu ma'lumotlar asosida USD, EUR
va RUB valyutalarining UZS'ga nisbatan kelgusi kunlardagi kursini bashorat
qiladi.

## Qanday ishlaydi

1. **Ma'lumot yig'ish** (`data/fetch_history.py`) — CBU arxividan kunma-kun
   so'nggi N yillik (standart 5 yil) kurslarni yuklab, `db/rates.sqlite3`
   SQLite bazasiga saqlaydi. Skript resumable — allaqachon yuklangan kunlar
   qayta so'ralmaydi.
2. **Model o'qitish** (`forecasting/train.py`) — har bir valyuta uchun
   [Prophet](https://facebook.github.io/prophet/) vaqt qatori modelini
   (trend + haftalik/yillik mavsumiylik) hamda zaxira sifatida oddiy
   trend+hafta-kuni modelini o'qitadi, so'nggi 30 kunlik ma'lumotda
   backtest qilib MAPE (o'rtacha foizli xatolik) hisoblaydi va eng aniq
   modelni tanlab `models/` papkasiga saqlaydi. Agar `prophet` o'rnatilmagan
   bo'lsa, bot baribir zaxira model bilan ishlayveradi.
3. **Telegram bot** (`bot/main.py`) — foydalanuvchiga joriy kurs, kelgusi
   kunlar bashorati va grafikni taqdim etadi hamda har kuni avtomatik
   ravishda yangi kursni yuklab, modellarni qayta o'qitadi
   (`bot/scheduler.py`).

## O'rnatish

```bash
git clone <repo>
cd taxmin-kurs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env faylida BOT_TOKEN qiymatini @BotFather'dan olingan token bilan to'ldiring
```

> **Eslatma:** `prophet` paketini o'rnatish bir necha daqiqa vaqt olishi
> mumkin (u ichida Stan modelini kompilyatsiya qiladi). Agar u ishlamasa,
> uni `requirements.txt` dan olib tashlashingiz mumkin — bot avtomatik
> ravishda zaxira modelga o'tadi.

## Ishga tushirish

```bash
# 1) So'nggi 5 yillik tarixni yuklab olish (bir martalik, biroz vaqt oladi)
python -m data.fetch_history --years 5 --currencies USD,EUR,RUB

# 2) Bashorat modellarini o'qitish
python -m forecasting.train

# 3) Botni ishga tushirish
python -m bot.main
```

Bot ishga tushgach, har kuni `.env` faylidagi `DAILY_UPDATE_HOUR` /
`DAILY_UPDATE_MINUTE` da (standart 09:05, `Asia/Tashkent`) avtomatik
ravishda yangi kursni yuklab, modellarni qayta o'qitadi — qo'lda qayta
ishga tushirish shart emas.

## Bot buyruqlari

| Buyruq | Tavsif |
|---|---|
| `/start` | Botni ishga tushirish, qisqacha tanishtirish |
| `/yordam` | Barcha buyruqlar bo'yicha yordam |
| `/kurs [USD\|EUR\|RUB]` | Joriy kursni ko'rsatadi |
| `/bashorat [valyuta] [kunlar]` | Kelgusi kunlar uchun bashorat (standart 7 kun, maksimal 30) va MAPE ko'rinishidagi taxminiy xatolik |
| `/grafik [valyuta]` | So'nggi 90 kunlik tarix + 14 kunlik bashorat grafigini rasm sifatida yuboradi |

Valyuta ko'rsatilmasa, bot inline tugmalar orqali tanlashni so'raydi.

## Loyiha tuzilishi

```
bot/                Telegram bot (aiogram 3): handlerlar, klaviatura, scheduler
data/                CBU API mijozi, SQLite ombori, tarix yuklovchi skript
forecasting/         Prophet + zaxira model, o'qitish va bashorat logikasi
charts/              Tarix/bashorat grafigini chizuvchi modul (matplotlib)
tests/               CBU mijozi va SQLite ombori uchun avtomatik testlar
```

## Testlarni ishga tushirish

```bash
python -m unittest discover -s tests -v
```

`tests/` papkasidagi testlar faqat standart kutubxona va `requests`
paketiga tayanadi (CBU API mijozi va SQLite ombori). Bashorat/grafik
modullari `pandas`, `numpy`, `prophet`, `matplotlib`, `aiogram` kabi
paketlarni talab qiladi — ularni sinash uchun avval
`pip install -r requirements.txt` bajarilishi kerak.

## Muhim eslatma

Bashorat statistik model (Prophet) asosida hisoblanadi va real bozor
omillarini (siyosiy voqealar, Markaziy bank qarorlari va h.k.) hisobga
olmaydi. Har bir bashorat bilan birga MAPE (backtest xatoligi) ko'rsatiladi
— bu modelning so'nggi 30 kunda qanchalik aniq ishlaganini bildiradi.
Bashorat moliyaviy qaror qabul qilish uchun yagona asos bo'lmasligi kerak.
