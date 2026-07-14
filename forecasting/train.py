"""Barcha sozlangan valyutalar uchun bashorat modellarini o'qituvchi CLI skript.

Ishga tushirish:
    python -m forecasting.train

Bu skriptni kunlik/haftalik jadval (cron yoki bot.scheduler) orqali qayta-qayta
ishga tushirish tavsiya etiladi, shunda modellar eng so'nggi ma'lumotlar bilan
yangilanib turadi.
"""

from __future__ import annotations

import argparse
import logging

from bot.config import settings
from data.storage import RateStorage
from forecasting.model import train_model

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bashorat modellarini o'qitish")
    parser.add_argument("--currencies", default=",".join(settings.currencies))
    parser.add_argument("--db-path", default=settings.db_path)
    parser.add_argument("--models-dir", default=settings.models_dir)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    storage = RateStorage(args.db_path)
    currencies = [c.strip().upper() for c in args.currencies.split(",") if c.strip()]
    for currency in currencies:
        history = storage.get_history(currency)
        try:
            result = train_model(currency, history, args.models_dir)
            logger.info("%s: model=%s, MAPE=%.2f%%", currency, result.model_name, result.mape)
        except ValueError as exc:
            logger.warning(str(exc))


if __name__ == "__main__":
    main()
