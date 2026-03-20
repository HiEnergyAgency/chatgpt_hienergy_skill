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
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from hienergy_client import HiEnergyClient


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = """
This MCP server exposes authenticated HiEnergy affiliate intelligence tools for ChatGPT.
Use the curated tools for common advertiser, deal, contact, publisher, and transaction
workflows. Use api_request when you need broader access to the authenticated /api surface.
This server also exposes discovery resources for the OpenAPI schema and curated tool catalog.
Return structured tool data first; let ChatGPT produce the final natural-language answer.
"""

OPENAPI_RESOURCE_URI = "openapi://project-rocket/schema"
TOOL_CATALOG_RESOURCE_URI = "tools://project-rocket/catalog"


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


def _compact(params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value not in (None, "", [], {})}


def _tool_catalog() -> List[Dict[str, Any]]:
    return [
        {"name": "search_advertisers", "description": "Search for advertisers by various criteria", "method": "GET", "endpoint": "/api/v1/advertisers"},
        {"name": "get_advertiser", "description": "Get detailed information about a specific advertiser", "method": "GET", "endpoint": "/api/v1/advertisers/{id}"},
        {"name": "get_similar_advertisers", "description": "Get similar advertisers for a given advertiser", "method": "GET", "endpoint": "/api/v1/advertisers/{id}/similar_advertisers"},
        {"name": "get_related_advertisers", "description": "Get related advertisers for a given advertiser", "method": "GET", "endpoint": "/api/v1/advertisers/{id}/related_advertisers"},
        {"name": "search_advertisers_by_domain", "description": "Search advertisers using the advertiser domain lookup endpoint", "method": "GET", "endpoint": "/api/v1/advertisers/search_by_domain"},
        {"name": "list_opportunities", "description": "List opportunity advertisers for the current scope", "method": "GET", "endpoint": "/api/v1/opportunities"},
        {"name": "search_transactions", "description": "Search for transactions by various criteria", "method": "GET", "endpoint": "/api/v1/transactions"},
        {"name": "get_transaction", "description": "Get detailed information about a specific transaction", "method": "GET", "endpoint": "/api/v1/transactions/{id}"},
        {"name": "search_deals", "description": "Search for deals by various criteria", "method": "GET", "endpoint": "/api/v1/deals"},
        {"name": "get_deal", "description": "Get detailed information about a specific deal", "method": "GET", "endpoint": "/api/v1/deals/{id}"},
        {"name": "search_contacts", "description": "Search contacts by domain, advertiser, email, or free-form query", "method": "GET", "endpoint": "/api/v1/contacts"},
        {"name": "search_domains", "description": "Search for advertisers by domain", "method": "GET", "endpoint": "/api/v1/domains/search"},
        {"name": "get_verticals", "description": "Get list of available verticals/industries", "method": "GET", "endpoint": "/api/v1/verticals"},
        {"name": "list_api_tools", "description": "List the API's published tool metadata", "method": "GET", "endpoint": "/api/v1/tools"},
        {"name": "get_api_schema", "description": "Fetch the OpenAPI schema for the authenticated API", "method": "GET", "endpoint": "/api/v1/schema"},
        {"name": "list_agencies", "description": "List agencies available to the current scope", "method": "GET", "endpoint": "/api/v1/agencies"},
        {"name": "get_agency", "description": "Get detailed information about a specific agency", "method": "GET", "endpoint": "/api/v1/agencies/{id}"},
        {"name": "list_networks", "description": "List affiliate networks available to the current scope", "method": "GET", "endpoint": "/api/v1/networks"},
        {"name": "get_network", "description": "Get detailed information about a specific network", "method": "GET", "endpoint": "/api/v1/networks/{id}"},
        {"name": "list_status_changes", "description": "Search advertiser status changes for the current scope", "method": "GET", "endpoint": "/api/v1/status_changes"},
        {"name": "list_tags", "description": "Search tags and categories", "method": "GET", "endpoint": "/api/v1/tags"},
        {"name": "get_tag_advertisers", "description": "List advertisers associated with a specific tag", "method": "GET", "endpoint": "/api/v1/tags/{id}/advertisers"},
        {"name": "generate_deeplink", "description": "Generate a deeplink for a destination URL or known program", "method": "POST", "endpoint": "/api/v1/deeplinks/generate"},
        {"name": "get_publisher", "description": "Get detailed information about a specific publisher", "method": "GET", "endpoint": "/api/v1/publishers/{id}"},
        {"name": "update_publisher", "description": "Update a publisher record", "method": "PATCH", "endpoint": "/api/v1/publishers/{id}"},
        {"name": "create_referred_user", "description": "Create a new user and automatically set the API caller as referred_by", "method": "POST", "endpoint": "/api/v1/users"},
        {"name": "create_publisher", "description": "Create a new publisher record (admin-only)", "method": "POST", "endpoint": "/api/v1/publishers"},
        {"name": "create_contact", "description": "Create a contact for an advertiser (admin-only endpoint)", "method": "POST", "endpoint": "/api/v1/contacts"},
        {"name": "add_contact", "description": "Add a contact for an advertiser (admin-only endpoint)", "method": "POST", "endpoint": "/api/v1/contacts"},
        {"name": "replace_contact", "description": "Reassign a contact to a different advertiser", "method": "POST", "endpoint": "/api/v1/contacts/{id}/replace"},
        {"name": "api_request", "description": "Call any authenticated JSON endpoint under /api/ to reach the app's broader API capabilities through MCP.", "method": "POST", "endpoint": "/api/{...}"},
        {"name": "get_advertiser_profile", "description": "Legacy alias for get_advertiser", "method": "GET", "endpoint": "/api/v1/advertisers/{id}"},
        {"name": "find_deals", "description": "Legacy alias for search_deals", "method": "GET", "endpoint": "/api/v1/deals"},
        {"name": "get_transactions", "description": "Legacy alias for search_transactions", "method": "GET", "endpoint": "/api/v1/transactions"},
        {"name": "search_affiliate_programs", "description": "Estimate affiliate-program matches using advertiser data", "method": "GET", "endpoint": "/api/v1/advertisers"},
    ]


def build_server(client: Optional[HiEnergyClient] = None) -> FastMCP:
    mcp = FastMCP(name="HiEnergy ChatGPT App", instructions=SERVER_INSTRUCTIONS)

    @lru_cache(maxsize=1)
    def get_client() -> HiEnergyClient:
        if client is not None:
            return client
        return HiEnergyClient()

    @mcp.custom_route("/", methods=["GET"])
    async def root(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "name": "HiEnergy ChatGPT App",
                "status": "ok",
                "mcp_endpoint": "/mcp",
                "transport": "streamable_http",
                "docs": "https://app.hienergy.ai/api_documentation/mcp",
            }
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    @mcp.tool()
    def search_advertisers(
        query: Optional[str] = None,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        network: Optional[str] = None,
        country: Optional[str] = None,
        vertical: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search advertisers by various criteria using the authenticated API.
        """
        return get_client().api_request(
            "/api/v1/advertisers",
            query=_compact(
                {
                    "name": name or query,
                    "domain": domain,
                    "network": network,
                    "country": country,
                    "vertical": vertical,
                    "limit": limit,
                    "cursor": cursor,
                }
            ),
        )

    @mcp.tool()
    def get_advertiser(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific advertiser.
        """
        return get_client().api_request(f"/api/v1/advertisers/{id}")

    @mcp.tool()
    def get_advertiser_profile(advertiser_id: str) -> Dict[str, Any]:
        """
        Legacy alias for get_advertiser.
        """
        advertiser = get_client().get_advertiser(advertiser_id)
        return _shape_advertiser(advertiser)

    @mcp.tool()
    def get_similar_advertisers(id: str) -> Dict[str, Any]:
        """
        Get similar advertisers for a given advertiser.
        """
        return get_client().api_request(f"/api/v1/advertisers/{id}/similar_advertisers")

    @mcp.tool()
    def get_related_advertisers(id: str) -> Dict[str, Any]:
        """
        Get related advertisers for a given advertiser.
        """
        return get_client().api_request(f"/api/v1/advertisers/{id}/related_advertisers")

    @mcp.tool()
    def search_advertisers_by_domain(
        domain: str,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search advertisers using the advertiser domain lookup endpoint.
        """
        return get_client().api_request(
            "/api/v1/advertisers/search_by_domain",
            query=_compact({"domain": domain, "limit": limit, "cursor": cursor}),
        )

    @mcp.tool()
    def list_opportunities(
        publisher_id: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List opportunity advertisers for the current scope.
        """
        return get_client().api_request(
            "/api/v1/opportunities",
            query=_compact(
                {
                    "publisher_id": publisher_id,
                    "sort": sort,
                    "order": order,
                    "page": page,
                    "per_page": per_page,
                    "limit": limit,
                }
            ),
        )

    @mcp.tool()
    def search_transactions(
        advertiser_id: Optional[str] = None,
        advertiser_slug: Optional[str] = None,
        network_id: Optional[str] = None,
        network_slug: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        currency: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        include_total: Optional[bool] = None,
        include_count: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for transactions by various criteria.
        """
        return get_client().api_request(
            "/api/v1/transactions",
            query=_compact(
                {
                    "advertiser_id": advertiser_id,
                    "advertiser_slug": advertiser_slug,
                    "network_id": network_id,
                    "network_slug": network_slug,
                    "start_date": start_date or date_from,
                    "end_date": end_date or date_to,
                    "currency": currency,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "page": page,
                    "per_page": per_page,
                    "include_total": include_total,
                    "include_count": include_count,
                    "limit": limit,
                }
            ),
        )

    @mcp.tool()
    def get_transaction(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific transaction.
        """
        return get_client().api_request(f"/api/v1/transactions/{id}")

    @mcp.tool()
    def search_deals(
        q: Optional[str] = None,
        advertiser_id: Optional[str] = None,
        advertiser_slug: Optional[str] = None,
        vertical_id: Optional[str] = None,
        vertical: Optional[str] = None,
        country: Optional[str] = None,
        status: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for deals by various criteria.
        """
        return get_client().api_request(
            "/api/v1/deals",
            query=_compact(
                {
                    "q": q,
                    "advertiser_id": advertiser_id,
                    "advertiser_slug": advertiser_slug,
                    "vertical_id": vertical_id,
                    "vertical": vertical,
                    "country": country,
                    "status": status,
                    "page": page,
                    "per_page": per_page,
                    "limit": limit,
                    "cursor": cursor,
                }
            ),
        )

    @mcp.tool()
    def get_deal(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific deal.
        """
        return get_client().api_request(f"/api/v1/deals/{id}")

    @mcp.tool()
    def find_deals(
        query: Optional[str] = None,
        country: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Legacy alias for search_deals.
        """
        status = "active" if active_only else None
        return search_deals(q=query, country=country, status=status, limit=limit)

    @mcp.tool()
    def search_contacts(
        q: Optional[str] = None,
        query: Optional[str] = None,
        domain: Optional[str] = None,
        advertiser_id: Optional[str] = None,
        advertiser_name: Optional[str] = None,
        email: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search contacts by domain, advertiser, email, or free-form query.
        """
        return get_client().api_request(
            "/api/v1/contacts",
            query=_compact(
                {
                    "q": q or query,
                    "domain": domain,
                    "advertiser_id": advertiser_id,
                    "advertiser_name": advertiser_name,
                    "email": email,
                    "page": page,
                    "per_page": per_page,
                    "limit": limit,
                }
            ),
        )

    @mcp.tool()
    def search_domains(
        domain: str,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for advertisers by domain.
        """
        return get_client().api_request(
            "/api/v1/domains/search",
            query=_compact({"domain": domain, "limit": limit, "cursor": cursor}),
        )

    @mcp.tool()
    def get_verticals(limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of available verticals/industries.
        """
        return get_client().api_request(
            "/api/v1/verticals",
            query=_compact({"limit": limit, "cursor": cursor}),
        )

    @mcp.resource(OPENAPI_RESOURCE_URI)
    def openapi_schema() -> Dict[str, Any]:
        """
        Full OpenAPI schema for the authenticated HiEnergy API.
        """
        return get_client().api_request("/api/v1/schema")

    @mcp.resource(TOOL_CATALOG_RESOURCE_URI)
    def curated_tool_catalog() -> Dict[str, Any]:
        """
        Human-oriented summary of the local curated tool catalog.
        """
        return {
            "server": "project_rocket_local",
            "note": "This local scaffold mirrors a broad subset of the hosted HiEnergy MCP server. Use api_request for unsupported endpoints.",
            "tools": _tool_catalog(),
        }

    @mcp.tool()
    def list_api_tools() -> Dict[str, Any]:
        """
        List the published tool metadata for this local scaffold.
        """
        return curated_tool_catalog()

    @mcp.tool()
    def get_api_schema() -> Dict[str, Any]:
        """
        Fetch the OpenAPI schema for the authenticated API.
        """
        return openapi_schema()

    @mcp.tool()
    def list_agencies(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List agencies available to the current scope.
        """
        return get_client().api_request(
            "/api/v1/agencies",
            query=_compact({"page": page, "per_page": per_page, "limit": limit}),
        )

    @mcp.tool()
    def get_agency(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific agency.
        """
        return get_client().api_request(f"/api/v1/agencies/{id}")

    @mcp.tool()
    def list_networks(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List affiliate networks available to the current scope.
        """
        return get_client().api_request(
            "/api/v1/networks",
            query=_compact({"page": page, "per_page": per_page, "limit": limit}),
        )

    @mcp.tool()
    def get_network(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific network.
        """
        return get_client().api_request(f"/api/v1/networks/{id}")

    @mcp.tool()
    def list_status_changes(
        q: Optional[str] = None,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        advertiser_id: Optional[int] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search advertiser status changes for the current scope.
        """
        return get_client().api_request(
            "/api/v1/status_changes",
            query=_compact(
                {
                    "q": q,
                    "from_status": from_status,
                    "to_status": to_status,
                    "advertiser_id": advertiser_id,
                    "page": page,
                    "per_page": per_page,
                    "limit": limit,
                }
            ),
        )

    @mcp.tool()
    def list_tags(
        search: Optional[str] = None,
        q: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search tags and categories.
        """
        return get_client().api_request(
            "/api/v1/tags",
            query=_compact({"search": search or q, "page": page, "per_page": per_page}),
        )

    @mcp.tool()
    def get_tag_advertisers(
        id: str,
        network_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List advertisers associated with a specific tag.
        """
        return get_client().api_request(
            f"/api/v1/tags/{id}/advertisers",
            query=_compact({"network_id": network_id, "status": status}),
        )

    @mcp.tool()
    def generate_deeplink(
        url: str,
        program_id: Optional[int] = None,
        custom_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a deeplink for a destination URL or known program.
        """
        return get_client().api_request(
            "/api/v1/deeplinks/generate",
            method="POST",
            body=_compact({"url": url, "program_id": program_id, "custom_code": custom_code}),
        )

    @mcp.tool()
    def get_publisher(id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific publisher.
        """
        return get_client().api_request(f"/api/v1/publishers/{id}")

    @mcp.tool()
    def update_publisher(id: str, publisher: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a publisher record.
        """
        return get_client().api_request(
            f"/api/v1/publishers/{id}",
            method="PATCH",
            body={"publisher": publisher},
        )

    @mcp.tool()
    def create_referred_user(user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user and automatically set the API caller as referred_by.
        """
        return get_client().api_request(
            "/api/v1/users",
            method="POST",
            body={"user": user},
        )

    @mcp.tool()
    def create_publisher(publisher: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new publisher record.
        """
        return get_client().api_request(
            "/api/v1/publishers",
            method="POST",
            body={"publisher": publisher},
        )

    @mcp.tool()
    def create_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a contact for an advertiser.
        """
        return get_client().api_request(
            "/api/v1/contacts",
            method="POST",
            body={"contact": contact},
        )

    @mcp.tool()
    def add_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a contact for an advertiser.
        """
        return create_contact(contact)

    @mcp.tool()
    def replace_contact(
        id: str,
        advertiser_id: Optional[int] = None,
        advertiser: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reassign a contact to a different advertiser.
        """
        replacement = advertiser or ({"id": advertiser_id} if advertiser_id is not None else None)
        if replacement is None:
            raise ValueError("advertiser_id or advertiser is required.")
        return get_client().api_request(
            f"/api/v1/contacts/{id}/replace",
            method="POST",
            body={"advertiser": replacement},
        )

    @mcp.tool()
    def api_request(
        path: str,
        method: str = "GET",
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call any authenticated JSON endpoint under /api/ to reach the broader API surface.
        """
        return get_client().api_request(
            path=path,
            method=method,
            query=query,
            body=body,
            idempotency_key=idempotency_key,
        )

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
    def get_transactions(
        advertiser_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Legacy alias for search_transactions that returns the simplified transaction shape.
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
    LOGGER.info("Expose the public /mcp URL to connect this app in ChatGPT.")
    if not os.environ.get("HIENERGY_API_KEY"):
        LOGGER.warning(
            "HIENERGY_API_KEY is not set. The server can start, but tool calls will fail "
            "until the key is configured."
        )
    server.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
