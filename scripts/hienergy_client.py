"""
Minimal HiEnergy API client used by the ChatGPT MCP server.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import requests


class HiEnergyClientError(RuntimeError):
    """Raised for recoverable client and API errors."""


class HiEnergyClient:
    """Thin wrapper around the HiEnergy API."""

    DEFAULT_BASE_URL = "https://app.hienergy.ai"
    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100
    REQUEST_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("HIENERGY_API_KEY")
        if not self.api_key:
            raise HiEnergyClientError(
                "HIENERGY_API_KEY is required. Export it before starting the server."
            )

        self.base_url = (base_url or os.environ.get("HIENERGY_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.session = session or requests.Session()
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "hienergy-chatgpt-app/1.0",
        }

    def _clamp_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return self.DEFAULT_LIMIT
        return max(1, min(int(limit), self.MAX_LIMIT))

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        clean_endpoint = endpoint.lstrip("/")
        if clean_endpoint.startswith(("http://", "https://")) or ".." in clean_endpoint:
            raise HiEnergyClientError("Invalid endpoint path.")

        url = f"{self.base_url}/api/v1/{clean_endpoint}"
        try:
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            body_preview = ""
            if exc.response is not None and exc.response.text:
                body_preview = exc.response.text[:300]
            raise HiEnergyClientError(
                f"HiEnergy API request failed (HTTP {status_code}): {body_preview}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise HiEnergyClientError(f"HiEnergy API request failed: {exc}") from exc

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return {}

        attributes = item.get("attributes")
        if isinstance(attributes, dict):
            normalized = dict(attributes)
            if "id" not in normalized and item.get("id") is not None:
                normalized["id"] = item.get("id")
            if item.get("type") is not None:
                normalized["type"] = item.get("type")
            return normalized

        return item

    def _extract_list(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        for wrapper_key in ("advertisers", "deals", "contacts", "transactions"):
            wrapped = payload.get(wrapper_key)
            if isinstance(wrapped, dict) and "data" in wrapped:
                return self._extract_list(wrapped)

        data = payload.get("data", [])
        if isinstance(data, list):
            return [self._normalize_item(item) for item in data]
        if isinstance(data, dict):
            return [self._normalize_item(data)]
        return []

    def _extract_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        items = self._extract_list(payload)
        return items[0] if items else {}

    def _looks_like_domain(self, value: str) -> bool:
        return bool(value and ("." in value or value.startswith(("http://", "https://"))))

    def _parse_commission_percent(self, item: Dict[str, Any]) -> Optional[float]:
        candidate_fields = (
            "commission_rate",
            "commission",
            "default_commission",
            "payout",
            "commission_details",
        )
        for field in candidate_fields:
            raw_value = item.get(field)
            if raw_value is None:
                continue
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", str(raw_value))
            if match:
                return float(match.group(1))
        return None

    def search_advertisers(self, query: Optional[str] = None, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        limit = self._clamp_limit(limit)
        if query and self._looks_like_domain(query):
            for field_name in ("domain", "url"):
                try:
                    response = self._request(
                        "advertisers/search_by_domain",
                        params={field_name: query, "limit": limit},
                    )
                    items = self._extract_list(response)
                    if items:
                        return items
                except HiEnergyClientError:
                    continue

        params: Dict[str, Any] = {"limit": limit}
        if query:
            params["search"] = query
        response = self._request("advertisers", params=params)
        return self._extract_list(response)

    def get_advertiser(self, advertiser_id: str) -> Dict[str, Any]:
        if not advertiser_id:
            raise HiEnergyClientError("advertiser_id is required.")
        response = self._request(f"advertisers/{advertiser_id}")
        return self._extract_one(response)

    def search_affiliate_programs(
        self,
        query: str,
        min_commission_percent: Optional[float] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        candidates = self.search_advertisers(query=query, limit=max(limit * 2, limit))
        results: List[Dict[str, Any]] = []
        for item in candidates:
            commission_percent = self._parse_commission_percent(item)
            if min_commission_percent is not None:
                if commission_percent is None or commission_percent < min_commission_percent:
                    continue
            enriched = dict(item)
            enriched["commission_percent_estimate"] = commission_percent
            results.append(enriched)
            if len(results) >= self._clamp_limit(limit):
                break
        return results

    def find_deals(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        active_only: bool = True,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "limit": self._clamp_limit(limit),
            "active": str(active_only).lower(),
        }
        if query:
            params["search"] = query
        if country:
            params["country"] = country
        response = self._request("deals", params=params)
        return self._extract_list(response)

    def search_contacts(self, query: Optional[str] = None, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": self._clamp_limit(limit)}
        if query:
            params["search"] = query
        response = self._request("contacts", params=params)
        return self._extract_list(response)

    def get_transactions(
        self,
        advertiser_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": self._clamp_limit(limit)}
        if advertiser_id:
            params["advertiser_id"] = advertiser_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        response = self._request("transactions", params=params)
        return self._extract_list(response)

