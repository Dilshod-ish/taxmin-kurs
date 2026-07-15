"""Bot birinchi marta ishga tushganda kerakli tarixiy ma'lumot va bashorat
modellarini avtomatik tayyorlaydi — terminalda qo'lda buyruq bajarish shart
emas. `AUTO_BOOTSTRAP=false` qilib o'chirish mumkin (masalan, agar tarix va
modellar allaqachon qo'lda tayyorlangan bo'lsa va qayta tekshirishni
xohlamasangiz)."""

from __future__ import annotations

import logging
from pathlib import Path

from bot.config import settings
from data.fetch_history import backfill
from data.storage import RateStorage
from forecasting.model import MIN_TRAINING_ROWS, train_model

logger = logging.getLogger(__name__)


def ensure_ready() -> None:
    storage = RateStorage(settings.db_path)

    missing_history = [
        currency
        for currency in settings.currencies
        if len(storage.get_existing_dates(currency)) < MIN_TRAINING_ROWS
    ]
    if missing_history:
        logger.info(
            "Tarixiy ma'lumot yetarli emas (%s), CBU'dan yuklab olinmoqda. "
            "Bu birinchi ishga tushirishda bir necha daqiqa vaqt olishi mumkin...",
            ", ".join(missing_history),
        )
        backfill(
            settings.currencies, settings.history_years, settings.db_path, settings.cbu_base_url
        )
    else:
        logger.info("Tarixiy ma'lumot bazada mavjud, yuklash o'tkazib yuborildi.")

    for currency in settings.currencies:
        model_path = Path(settings.models_dir) / f"{currency}.pkl"
        if model_path.exists():
            continue
        history = storage.get_history(currency)
        try:
            result = train_model(currency, history, settings.models_dir)
            logger.info(
                "%s modeli o'qitildi: %s (MAPE=%.2f%%)", currency, result.model_name, result.mape
            )
        except ValueError as exc:
            logger.warning(str(exc))
