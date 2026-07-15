# Taxmin Kurs — O'zbek so'miga nisbatan valyuta kursi bashoratchi Telegram bot

Botga valyuta nomini yozing — **USD**, **EUR** yoki **RUB** — bot sizga
**oxirgi 7 kunlik haqiqiy kurs** va **keyingi 7 kunlik bashoratni** bitta
rasmda qaytaradi. Alohida "ma'lumot yuklash" yoki "modelni o'qitish"
bosqichlarini qo'lda bajarish shart emas — bot buni so'rov kelganda o'zi
amalga oshiradi.

## Qanday ishlaydi

Foydalanuvchi valyuta nomini yozganda (`bot/handlers/forecast_chart.py`):

1. **Ma'lumotni tekshiradi** — SQLite bazasida (`db/rates.sqlite3`) shu
   valyuta uchun yetarli tarix bor-yo'qligini tekshiradi.
2. **Kerak bo'lsa yuklaydi** — yetishmayotgan kunlarni CBU (O'zbekiston
   Markaziy banki) rasmiy JSON arxividan parallel so'rovlar bilan tez
   yuklab oladi (`data/fetch_history.py`). Birinchi so'rovda bu bir necha
   o'nlab soniya olishi mumkin, keyingi so'rovlarda deyarli oniy.
3. **Modelni o'qitadi** — agar model hali bugun uchun o'qitilmagan bo'lsa,
   [Prophet](https://facebook.github.io/prophet/) vaqt qatori modelini
   (yoki `prophet` o'rnatilmagan bo'lsa, oddiy trend+mavsumiylik zaxira
   modelini) o'qitadi, so'nggi 30 kunda backtest qilib aniqlikni (MAPE)
   hisoblaydi (`forecasting/model.py`). Shu kunning keyingi so'rovlari
   uchun qayta o'qitmaydi — natija keshlanadi.
4. **Rasm chizadi va yuboradi** — oxirgi 7 kun (haqiqiy) va keyingi 7 kun
   (bashorat, ishonch oralig'i bilan) bitta grafikda, har bir nuqtada aniq
   raqam bilan (`charts/plot.py`).

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
> mumkin. Agar u ishlamasa, `requirements.txt`dan olib tashlashingiz
> mumkin — bot avtomatik ravishda zaxira modelga o'tadi.

## Ishga tushirish

```bash
python -m bot.main
```

Shu bilan tamom — Telegram'da botga `/start` yozing, keyin `USD`, `EUR`
yoki `RUB` deb yozing. Bot birinchi so'rovda ma'lumotni yig'ib, tahlil
qilib, rasm shaklida javob beradi.

## Bot bilan muloqot

| Xabar | Natija |
|---|---|
| `/start` | Botni tanishtirish, valyuta tugmalari |
| `/yordam` | Qisqacha yo'riqnoma |
| `USD` (yoki `EUR`, `RUB`) | So'nggi 7 kun + keyingi 7 kunlik bashorat, bitta rasmda |

Valyutani tugma orqali ham tanlash mumkin (`/start` bosilganda chiqadigan
klaviatura orqali).

## Loyiha tuzilishi

```
bot/                 Telegram bot (aiogram 3): handlerlar, klaviatura
data/                CBU API mijozi, SQLite ombori, tarixni tezkor yuklash
forecasting/         Prophet + zaxira model, on-demand o'qitish va bashorat
charts/              Oxirgi 7 kun + keyingi 7 kunni bitta rasmda chizish
tests/                CBU mijozi va SQLite ombori uchun avtomatik testlar
```

## Sozlamalar (`.env`)

| O'zgaruvchi | Vazifasi | Standart |
|---|---|---|
| `BOT_TOKEN` | Telegram bot tokeni | — (majburiy) |
| `CURRENCIES` | Qo'llab-quvvatlanadigan valyutalar | `USD,EUR,RUB` |
| `HISTORY_WINDOW_DAYS` | Model uchun ishlatiladigan tarix uzunligi (kunlarda) | `400` |
| `DB_PATH` | SQLite fayli manzili | `db/rates.sqlite3` |
| `MODELS_DIR` | O'qitilgan modellar saqlanadigan papka | `models` |
| `CBU_BASE_URL` | CBU API manzili | `https://cbu.uz` |

## Testlarni ishga tushirish

```bash
python -m unittest discover -s tests -v
```

`tests/` papkasidagi testlar faqat standart kutubxona va `requests`
paketiga tayanadi (CBU API mijozi va SQLite ombori). Bashorat/grafik
modullarini sinash uchun avval `pip install -r requirements.txt`
bajarilishi kerak.

## Muhim eslatma

Bashorat statistik model (Prophet) asosida hisoblanadi va real bozor
omillarini (siyosiy voqealar, Markaziy bank qarorlari va h.k.) hisobga
olmaydi. Har bir bashorat bilan birga MAPE (backtest xatoligi) ko'rsatiladi
— bu modelning so'nggi 30 kunda qanchalik aniq ishlaganini bildiradi.
Bashorat moliyaviy qaror qabul qilish uchun yagona asos bo'lmasligi kerak.
