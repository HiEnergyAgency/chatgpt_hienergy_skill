# HiEnergy MCP App

This repository helps you work with HiEnergy through MCP in two ways:

- Use the hosted HiEnergy MCP server at `https://app.hienergy.ai/mcp`
- Run the local FastMCP scaffold in this repo for development

If you already have a HiEnergy API key, the hosted MCP server is the recommended path.

## What this repo includes

- A reusable HiEnergy API client in `scripts/hienergy_client.py`
- A local FastMCP scaffold in `scripts/hienergy_chatgpt_server.py`
- A local curated MCP tool set plus a generic `api_request` bridge and discovery resources
- Setup notes for ChatGPT, Codex, the Responses API, and local development
- Unit tests for the API client

## Recommended quick start

### ChatGPT

Create a remote MCP app using:

```text
https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY
```

Choose `No Authentication` in the ChatGPT setup flow because the URL already contains the API key.

Treat that URL like a secret. If it is shared, rotate the key.

### Codex

Add the hosted MCP server directly:

```bash
codex mcp add hienergy --url "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY"
```

Verify it:

```bash
codex mcp list
codex mcp get hienergy
```

### Responses API

Use an MCP tool block like this:

```json
{
  "type": "mcp",
  "server_label": "hienergy",
  "server_url": "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY",
  "require_approval": "never"
}
```

## Direct MCP usage

The hosted server accepts JSON-RPC requests on `/mcp`. For low-level clients, authenticate with the standard HiEnergy API key in the `X-Api-Key` header.

Example `initialize` request:

```bash
curl -X POST https://app.hienergy.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -H "MCP-Protocol-Version: 2025-11-25" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-11-25",
      "capabilities": {},
      "clientInfo": { "name": "My MCP Client", "version": "1.0.0" }
    }
  }'
```

Example `tools/list` request:

```bash
curl -X POST https://app.hienergy.ai/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

The hosted server exposes curated MCP tools plus a broader `api_request` bridge for the authenticated HiEnergy API surface.

## Local development scaffold

Use the local server only when you want to build or test the MCP implementation in this repo. The local scaffold is separate from the hosted HiEnergy production MCP server.

Python 3.10+ is recommended. The FastMCP dependency used by the local scaffold does not install cleanly in the default Python 3.9 runtime on this machine.

### 1. Install dependencies

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
export HIENERGY_API_KEY="<your_api_key>"
```

Optional:

```bash
export HIENERGY_BASE_URL="https://app.hienergy.ai"
export PORT="8000"
```

### 3. Run the local MCP server

```bash
python3 scripts/hienergy_chatgpt_server.py
```

The local server starts on `http://0.0.0.0:8000` by default and exposes FastMCP streamable HTTP over `/mcp`.

It also exposes:

- `/health` for deployment health checks
- `/` for a simple JSON status page

### 4. Expose the local server if needed

If you want to test the local scaffold from ChatGPT, expose it through a public HTTPS URL and use the `/mcp` path.

## Local tool surface

The local scaffold now mirrors a broader subset of the hosted HiEnergy MCP docs:

- Advertiser discovery and detail tools such as `search_advertisers`, `get_advertiser`, `get_similar_advertisers`, and `get_related_advertisers`
- Search and reporting tools for deals, transactions, contacts, domains, verticals, agencies, networks, status changes, and tags
- Discovery helpers `list_api_tools`, `get_api_schema`, `resources/list`, and `resources/read`
- Admin and workflow tools such as `create_contact`, `add_contact`, `replace_contact`, `create_referred_user`, `create_publisher`, `update_publisher`, and `generate_deeplink`
- The generic `api_request` bridge for authenticated `/api` access beyond the curated wrappers

The hosted HiEnergy MCP server still has the most complete production surface. Use `api_request` from the local scaffold when you need an authenticated endpoint that is not yet wrapped as a named local tool.

## Render deployment

This repo includes `render.yaml` for deploying the local scaffold as a web service.

- The local service starts even if `HIENERGY_API_KEY` is not configured yet.
- Tool calls fail with a clear error until you add that secret.
- Render health checks use `/health`.
- The deployed local scaffold uses `/mcp`.
- The hosted HiEnergy production MCP server uses `/mcp`.

## Example direct API client usage

```bash
python3 example_usage.py
```

## Testing

Run the unit tests:

```bash
python3 -m unittest test_hienergy_client.py -v
```

Optional smoke test against the hosted MCP server:

```bash
python3 - <<'PY'
import requests

url = "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "MCP-Protocol-Version": "2025-11-25",
}
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "README smoke test", "version": "1.0.0"},
    },
}
response = requests.post(url, headers=headers, json=payload, timeout=30)
print(response.status_code)
print(response.json().get("result", {}).get("serverInfo", {}))
PY
```

## Notes

- Prefer the hosted `/mcp` endpoint for real usage.
- Use the local scaffold when you need to change server behavior in this repo.
- Add OAuth before sharing this in a broader workspace or production environment.
