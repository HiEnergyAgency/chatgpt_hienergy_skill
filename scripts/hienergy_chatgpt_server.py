"""
FastMCP server that exposes HiEnergy tools to ChatGPT.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from hienergy_client import HiEnergyClient


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = """
This MCP server exposes read-only HiEnergy affiliate intelligence tools for ChatGPT.
Use these tools to search advertisers, inspect advertiser profiles, research affiliate
programs, review active deals, find contacts, and retrieve light transaction data.
Return structured tool data first; let ChatGPT produce the final natural-language answer.
"""


def _deep_link(advertiser_id: Optional[Any]) -> Optional[str]:
    if advertiser_id in (None, ""):
        return None
    return f"https://app.hienergy.ai/a/{advertiser_id}"


def _shape_advertiser(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "domain": item.get("domain"),
        "url": item.get("url"),
        "status": item.get("status"),
        "network_name": item.get("network_name"),
        "publisher_name": item.get("publisher_name"),
        "commission_rate": item.get("commission_rate"),
        "app_url": _deep_link(item.get("id")),
    }


def _shape_deal(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "advertiser_name": item.get("advertiser_name"),
        "description": item.get("description"),
        "country": item.get("country"),
        "payout": item.get("payout"),
        "starts_at": item.get("starts_at"),
        "ends_at": item.get("ends_at"),
    }


def _shape_contact(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "title": item.get("title"),
        "email": item.get("email"),
        "linkedin_url": item.get("linkedin_url"),
        "advertiser_name": item.get("advertiser_name"),
    }


def _shape_transaction(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "advertiser_id": item.get("advertiser_id"),
        "advertiser_name": item.get("advertiser_name"),
        "status": item.get("status"),
        "sale_amount": item.get("sale_amount"),
        "commission_amount": item.get("commission_amount"),
        "currency": item.get("currency"),
        "transaction_date": item.get("transaction_date"),
    }


def build_server(client: Optional[HiEnergyClient] = None) -> FastMCP:
    mcp = FastMCP(name="HiEnergy ChatGPT App", instructions=SERVER_INSTRUCTIONS)

    @lru_cache(maxsize=1)
    def get_client() -> HiEnergyClient:
        if client is not None:
            return client
        return HiEnergyClient()

    @mcp.tool()
    def search_advertisers(query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search HiEnergy advertisers by brand name, domain, or URL.
        Returns structured advertiser results for ChatGPT to summarize.
        """
        results = get_client().search_advertisers(query=query, limit=limit)
        return {
            "query": query,
            "count": len(results),
            "results": [_shape_advertiser(item) for item in results],
        }

    @mcp.tool()
    def get_advertiser_profile(advertiser_id: str) -> Dict[str, Any]:
        """
        Fetch a single HiEnergy advertiser profile by advertiser id.
        """
        advertiser = get_client().get_advertiser(advertiser_id)
        return _shape_advertiser(advertiser)

    @mcp.tool()
    def search_affiliate_programs(
        query: str,
        min_commission_percent: Optional[float] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search affiliate programs using advertiser data, optionally filtered by minimum commission percent.
        """
        results = get_client().search_affiliate_programs(
            query=query,
            min_commission_percent=min_commission_percent,
            limit=limit,
        )
        shaped_results: List[Dict[str, Any]] = []
        for item in results:
            shaped = _shape_advertiser(item)
            shaped["commission_percent_estimate"] = item.get("commission_percent_estimate")
            shaped_results.append(shaped)
        return {
            "query": query,
            "count": len(shaped_results),
            "min_commission_percent": min_commission_percent,
            "results": shaped_results,
        }

    @mcp.tool()
    def find_deals(
        query: Optional[str] = None,
        country: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Find HiEnergy deals with optional search text, country, and active filter.
        """
        results = get_client().find_deals(
            query=query,
            country=country,
            active_only=active_only,
            limit=limit,
        )
        return {
            "query": query,
            "country": country,
            "active_only": active_only,
            "count": len(results),
            "results": [_shape_deal(item) for item in results],
        }

    @mcp.tool()
    def search_contacts(query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search HiEnergy partner contacts by name, company, or query string.
        """
        results = get_client().search_contacts(query=query, limit=limit)
        return {
            "query": query,
            "count": len(results),
            "results": [_shape_contact(item) for item in results],
        }

    @mcp.tool()
    def get_transactions(
        advertiser_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Retrieve HiEnergy transactions with optional advertiser and date filters.
        """
        results = get_client().get_transactions(
            advertiser_id=advertiser_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return {
            "advertiser_id": advertiser_id,
            "start_date": start_date,
            "end_date": end_date,
            "count": len(results),
            "results": [_shape_transaction(item) for item in results],
        }

    return mcp


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = build_server()
    LOGGER.info("Starting HiEnergy MCP server on 0.0.0.0:%s", port)
    LOGGER.info("Expose the public /sse/ URL to connect this app in ChatGPT.")
    if not os.environ.get("HIENERGY_API_KEY"):
        LOGGER.warning(
            "HIENERGY_API_KEY is not set. The server can start, but tool calls will fail "
            "until the key is configured."
        )
    server.run(transport="sse", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
