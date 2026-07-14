"""O'zbekiston Respublikasi Markaziy banki (CBU) valyuta kurslari API mijozi."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CBU_DATE_FORMAT = "%d.%m.%Y"
DEFAULT_BASE_URL = "https://cbu.uz"
DEFAULT_LANG = "uz"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


class CbuApiError(RuntimeError):
    """CBU API kutilmagan javob qaytarganda ko'tariladi."""


@dataclass(frozen=True)
class ExchangeRate:
    currency: str
    rate: float
    rate_date: date
    diff: float = 0.0


class CbuClient:
    """cbu.uz saytining rasmiy JSON arxiv API'siga so'rov yuboruvchi mijoz."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        lang: str = DEFAULT_LANG,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.session = session or requests.Session()

    def _get(self, path: str) -> list:
        url = f"{self.base_url}/{self.lang}/arkhiv-kursov-valyut/json/{path}"
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise CbuApiError(f"Kutilmagan javob formati: {url}")
                return payload
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "CBU so'rovi muvaffaqiyatsiz (%s/%s urinish): %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        raise CbuApiError(f"CBU API'dan ma'lumot olib bo'lmadi: {url}") from last_error

    @staticmethod
    def _parse_entry(entry: dict) -> ExchangeRate:
        try:
            rate_date = datetime.strptime(entry["Date"], CBU_DATE_FORMAT).date()
            return ExchangeRate(
                currency=entry["Ccy"],
                rate=float(entry["Rate"]),
                rate_date=rate_date,
                diff=float(entry.get("Diff") or 0.0),
            )
        except (KeyError, ValueError) as exc:
            raise CbuApiError(f"Kutilmagan yozuv formati: {entry}") from exc

    def get_current_rates(self) -> list[ExchangeRate]:
        """Barcha valyutalarning bugungi kursini qaytaradi."""
        payload = self._get("")
        return [self._parse_entry(e) for e in payload]

    def get_rates_for_date(self, target_date: date) -> list[ExchangeRate]:
        """Berilgan sana uchun barcha valyutalar kursini qaytaradi."""
        path = f"all/{target_date.strftime(CBU_DATE_FORMAT)}/"
        payload = self._get(path)
        return [self._parse_entry(e) for e in payload]

    def get_rate_for_date(self, currency: str, target_date: date) -> Optional[ExchangeRate]:
        """Berilgan sana uchun bitta valyuta kursini qaytaradi (mavjud bo'lmasa None)."""
        path = f"{currency}/{target_date.strftime(CBU_DATE_FORMAT)}/"
        payload = self._get(path)
        if not payload:
            return None
        return self._parse_entry(payload[0])
