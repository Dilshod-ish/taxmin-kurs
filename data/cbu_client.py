"""O'zbekiston Respublikasi Markaziy banki (CBU) valyuta kurslari API mijozi.

Haqiqiy so'rov mexanizmi cbu.uz arxiv sahifasining o'zi (brauzer DevTools
Network paneli orqali) tekshirib aniqlangan:

- Manzil har doim bitta: https://cbu.uz/common/json/
- GET so'rov — joriy (bugungi) kursni qaytaradi.
- POST so'rov, "date" maydoni bilan (DD/MM/YYYY formatida, masalan
  "03/07/2026") — o'sha tarixiy sana uchun kursni qaytaradi.

(Eslatma: dastlab boshqa, hujjatlashtirilmagan "/arkhiv-kursov-valyut/
json/all/{sana}/" manzili ishlatilgan edi — u har doim joriy sanani
qaytarardi, sanani e'tiborsiz qoldirardi, shuning uchun almashtirildi.)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

REQUEST_DATE_FORMAT = "%d/%m/%Y"
RESPONSE_DATE_FORMAT = "%d.%m.%Y"
DEFAULT_BASE_URL = "https://cbu.uz"
REQUEST_TIMEOUT = 8
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1


class CbuApiError(RuntimeError):
    """CBU API kutilmagan javob qaytarganda ko'tariladi."""


@dataclass(frozen=True)
class ExchangeRate:
    currency: str
    rate: float
    rate_date: date
    diff: float = 0.0


REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}


class CbuClient:
    """cbu.uz saytining common/json/ endpointiga so'rov yuboruvchi mijoz.

    `X-Requested-With: XMLHttpRequest` sarlavhasi majburiy — brauzer
    DevTools orqali tekshirilganda, bu sarlavha bo'lmasa server so'ralgan
    sanani e'tiborsiz qoldirib, doim joriy kursni qaytarishi aniqlandi
    (Bitrix CMS'ning odatiy AJAX tekshiruvi bo'lsa kerak). `Referer` va
    `Origin` esa sessiya boshlanishi bilan avtomatik o'rnatiladi."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update(REQUIRED_HEADERS)
        self.session.headers.setdefault("Referer", f"{self.base_url}/uz/arkhiv-kursov-valyut/")
        self.session.headers.setdefault("Origin", self.base_url)

    def _request(self, *, post_data: Optional[dict] = None) -> list:
        url = f"{self.base_url}/common/json/"
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if post_data is not None:
                    response = self.session.post(url, data=post_data, timeout=REQUEST_TIMEOUT)
                else:
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
    def _parse_entry(entry: dict, override_date: Optional[date] = None) -> ExchangeRate:
        """`override_date` berilsa, natijaga shu sana yopishtiriladi (CBU javobidagi
        "Date" maydoniga emas) — ehtiyot chorasi sifatida, agar server sanani
        kutilganidek qaytarmasa ham, ma'lumot to'g'ri kunga yozilishini
        kafolatlash uchun."""
        try:
            response_date = datetime.strptime(entry["Date"], RESPONSE_DATE_FORMAT).date()
            rate_date = override_date if override_date is not None else response_date
            if override_date is not None and response_date != override_date:
                logger.warning(
                    "CBU javobidagi sana (%s) so'ralgan sanadan (%s) farq qiladi — "
                    "so'ralgan sana ishlatiladi",
                    response_date,
                    override_date,
                )
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
        payload = self._request()
        return [self._parse_entry(e) for e in payload]

    def get_rates_for_date(self, target_date: date) -> list[ExchangeRate]:
        """Berilgan sana uchun barcha valyutalar kursini qaytaradi."""
        payload = self._request(post_data={"date": target_date.strftime(REQUEST_DATE_FORMAT)})
        return [self._parse_entry(e, override_date=target_date) for e in payload]
