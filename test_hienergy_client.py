import os
import unittest
from unittest.mock import Mock, patch

from scripts.hienergy_client import HiEnergyClient, HiEnergyClientError


class TestHiEnergyClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = HiEnergyClient(api_key="test-key")

    def test_initialization_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HiEnergyClientError):
                HiEnergyClient()

    def test_initialization_uses_environment(self) -> None:
        with patch.dict(os.environ, {"HIENERGY_API_KEY": "env-key"}, clear=True):
            client = HiEnergyClient()
            self.assertEqual(client.api_key, "env-key")

    @patch("scripts.hienergy_client.requests.Session.request")
    def test_search_advertisers_uses_domain_endpoint_for_domain_queries(self, mock_request: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "data": [{"id": "1", "attributes": {"name": "Alo Yoga", "domain": "aloyoga.com"}}]
        }
        response.raise_for_status = Mock()
        mock_request.return_value = response

        results = self.client.search_advertisers("aloyoga.com", limit=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alo Yoga")
        self.assertEqual(mock_request.call_args.args[0], "GET")
        self.assertIn("/advertisers/search_by_domain", mock_request.call_args.args[1])

    @patch("scripts.hienergy_client.requests.Session.request")
    def test_get_advertiser_returns_single_normalized_record(self, mock_request: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "data": {"id": "42", "attributes": {"name": "HiEnergy Brand", "status": "active"}}
        }
        response.raise_for_status = Mock()
        mock_request.return_value = response

        result = self.client.get_advertiser("42")

        self.assertEqual(result["id"], "42")
        self.assertEqual(result["name"], "HiEnergy Brand")

    @patch("scripts.hienergy_client.requests.Session.request")
    def test_search_affiliate_programs_filters_on_min_commission(self, mock_request: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "data": [
                {"id": "1", "attributes": {"name": "Low", "commission_rate": "5%"}},
                {"id": "2", "attributes": {"name": "High", "commission_rate": "12%"}},
                {"id": "3", "attributes": {"name": "Unknown", "commission_rate": "CPA only"}},
            ]
        }
        response.raise_for_status = Mock()
        mock_request.return_value = response

        results = self.client.search_affiliate_programs(
            "supplements",
            min_commission_percent=10,
            limit=10,
        )

        self.assertEqual([item["name"] for item in results], ["High"])
        self.assertEqual(results[0]["commission_percent_estimate"], 12.0)

    @patch("scripts.hienergy_client.requests.Session.request")
    def test_find_deals_passes_expected_filters(self, mock_request: Mock) -> None:
        response = Mock()
        response.json.return_value = {"data": []}
        response.raise_for_status = Mock()
        mock_request.return_value = response

        self.client.find_deals(query="wellness", country="US", active_only=True, limit=7)

        self.assertEqual(mock_request.call_args.args[0], "GET")
        params = mock_request.call_args.kwargs["params"]
        self.assertEqual(params["search"], "wellness")
        self.assertEqual(params["country"], "US")
        self.assertEqual(params["active"], "true")
        self.assertEqual(params["limit"], 7)

    @patch("scripts.hienergy_client.requests.Session.request")
    def test_api_request_uses_absolute_api_path_and_idempotency_header(self, mock_request: Mock) -> None:
        response = Mock()
        response.json.return_value = {"data": {"ok": True}}
        response.raise_for_status = Mock()
        mock_request.return_value = response

        payload = self.client.api_request(
            path="/api/v1/publishers/42",
            method="PATCH",
            body={"publisher": {"name": "Updated"}},
            idempotency_key="abc123",
        )

        self.assertEqual(payload["data"]["ok"], True)
        self.assertEqual(mock_request.call_args.args[0], "PATCH")
        self.assertTrue(mock_request.call_args.args[1].endswith("/api/v1/publishers/42"))
        self.assertEqual(mock_request.call_args.kwargs["json"], {"publisher": {"name": "Updated"}})
        self.assertEqual(
            mock_request.call_args.kwargs["headers"]["Idempotency-Key"],
            "abc123",
        )

    def test_api_request_rejects_non_api_paths(self) -> None:
        with self.assertRaises(HiEnergyClientError):
            self.client.api_request("/mcp")


if __name__ == "__main__":
    unittest.main()
