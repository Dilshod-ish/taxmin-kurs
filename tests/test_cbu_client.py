import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import requests

from data.cbu_client import CbuApiError, CbuClient

SAMPLE_ENTRY = {
    "id": 210,
    "Code": "840",
    "Ccy": "USD",
    "CcyNm_EN": "US Dollar",
    "Nominal": "1",
    "Rate": "12750.50",
    "Diff": "15.20",
    "Date": "14.07.2026",
}


class CbuClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = CbuClient(session=MagicMock())

    def test_parse_entry(self) -> None:
        rate = CbuClient._parse_entry(SAMPLE_ENTRY)
        self.assertEqual(rate.currency, "USD")
        self.assertEqual(rate.rate, 12750.50)
        self.assertEqual(rate.rate_date, date(2026, 7, 14))
        self.assertEqual(rate.diff, 15.20)

    def test_parse_entry_missing_field_raises(self) -> None:
        broken = dict(SAMPLE_ENTRY)
        del broken["Rate"]
        with self.assertRaises(CbuApiError):
            CbuClient._parse_entry(broken)

    def test_get_current_rates(self) -> None:
        response = MagicMock()
        response.json.return_value = [SAMPLE_ENTRY]
        response.raise_for_status.return_value = None
        self.client.session.get.return_value = response

        rates = self.client.get_current_rates()

        self.assertEqual(len(rates), 1)
        self.assertEqual(rates[0].currency, "USD")
        called_url = self.client.session.get.call_args.args[0]
        self.assertTrue(called_url.endswith("/arkhiv-kursov-valyut/json/"))

    def test_get_rates_for_date_builds_correct_url(self) -> None:
        response = MagicMock()
        response.json.return_value = [SAMPLE_ENTRY]
        response.raise_for_status.return_value = None
        self.client.session.get.return_value = response

        self.client.get_rates_for_date(date(2026, 7, 14))

        called_url = self.client.session.get.call_args.args[0]
        self.assertTrue(called_url.endswith("/arkhiv-kursov-valyut/json/all/14.07.2026/"))

    def test_get_rate_for_date_returns_none_on_empty_payload(self) -> None:
        response = MagicMock()
        response.json.return_value = []
        response.raise_for_status.return_value = None
        self.client.session.get.return_value = response

        result = self.client.get_rate_for_date("USD", date(2026, 1, 1))

        self.assertIsNone(result)

    def test_retries_then_raises(self) -> None:
        self.client.session.get.side_effect = requests.ConnectionError("boom")
        with patch("data.cbu_client.time.sleep"):
            with self.assertRaises(CbuApiError):
                self.client.get_current_rates()
        self.assertEqual(self.client.session.get.call_count, 2)

    def test_recovers_after_transient_failure(self) -> None:
        ok_response = MagicMock()
        ok_response.json.return_value = [SAMPLE_ENTRY]
        ok_response.raise_for_status.return_value = None
        self.client.session.get.side_effect = [requests.ConnectionError("boom"), ok_response]

        with patch("data.cbu_client.time.sleep"):
            rates = self.client.get_current_rates()

        self.assertEqual(len(rates), 1)


if __name__ == "__main__":
    unittest.main()
