import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _split_currencies(raw: str) -> list[str]:
    return [c.strip().upper() for c in raw.split(",") if c.strip()]


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "db" / "rates.sqlite3"))
    models_dir: str = os.getenv("MODELS_DIR", str(BASE_DIR / "models"))
    currencies: list[str] = field(
        default_factory=lambda: _split_currencies(os.getenv("CURRENCIES", "USD,EUR,RUB"))
    )
    cbu_base_url: str = os.getenv("CBU_BASE_URL", "https://cbu.uz")
    history_years: int = int(os.getenv("HISTORY_YEARS", "5"))
    timezone: str = os.getenv("TIMEZONE", "Asia/Tashkent")
    daily_update_hour: int = int(os.getenv("DAILY_UPDATE_HOUR", "9"))
    daily_update_minute: int = int(os.getenv("DAILY_UPDATE_MINUTE", "5"))
    max_forecast_days: int = int(os.getenv("MAX_FORECAST_DAYS", "30"))


settings = Settings()
