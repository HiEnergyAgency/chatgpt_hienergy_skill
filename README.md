# HiEnergy ChatGPT App

This repository is a ChatGPT-oriented version of the existing HiEnergy OpenClaw skill.

It supports two paths:

- Connect directly to the hosted HiEnergy MCP server at `https://app.hienergy.ai/mcp`
- Run the local FastMCP scaffold in this repo for development or experimentation

## What it includes

- A reusable HiEnergy API client in `scripts/hienergy_client.py`
- A FastMCP server in `scripts/hienergy_chatgpt_server.py`
- Read-only tools for advertisers, affiliate programs, deals, contacts, and transactions
- Setup notes for the hosted MCP server, local development, and ChatGPT/Codex connection
- Unit tests for the API client

## Quick start

## Use the hosted HiEnergy MCP server

If you already have a HiEnergy API key, prefer the hosted MCP server instead of running the local scaffold.

### ChatGPT

Use the ChatGPT-ready server URL and choose `No Authentication` in the app setup flow:

```text
https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY
```

Treat that URL like a secret because it embeds your API key directly.

### Codex

```bash
codex mcp add hienergy --url "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY"
```

### Responses API

```json
{
  "type": "mcp",
  "server_label": "hienergy",
  "server_url": "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY",
  "require_approval": "never"
}
```

## Run the local scaffold

Python 3.10+ is recommended for this repo. The FastMCP package used by the server does not install in the default Python 3.9 runtime on this machine.

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

### 3. Run the MCP server

```bash
python3 scripts/hienergy_chatgpt_server.py
```

The server starts on `http://0.0.0.0:8000` by default and exposes the FastMCP SSE transport at `/sse`.

## Connecting to ChatGPT

Preferred production path:

1. Use the hosted HiEnergy MCP server at `https://app.hienergy.ai/mcp`.
2. For ChatGPT, paste the full server URL with `?api_key=YOUR_API_KEY` and choose `No Authentication`.
3. For Codex or other MCP clients, connect to `/mcp` and authenticate with the same HiEnergy API key.

Local development path:

1. Expose the local server over HTTPS, for example with a tunnel or deployment target.
2. Use the public URL ending in `/sse`.
3. Import that server into ChatGPT as a custom MCP app if you want to test the local scaffold.

This repo keeps all tools read-only so it is safe to test before adding any write actions.

## Render deployment

This repo includes `render.yaml` for a simple web-service deploy on Render.

- The service starts even if `HIENERGY_API_KEY` is not configured yet.
- Tool calls will fail with a clear error until you add that secret in Render.
- The local scaffold still expects the deployed base URL plus `/sse`.
- The hosted HiEnergy production MCP server uses `/mcp`.

## Available tools

### `search_advertisers`

Search advertisers by brand name, domain, or URL.

### `get_advertiser_profile`

Fetch a single advertiser profile, including the HiEnergy deep link.

### `search_affiliate_programs`

Find advertiser/program candidates and optionally filter by minimum commission percent.

### `find_deals`

Look up deals by search term with optional country and active-only filters.

### `search_contacts`

Find partner contacts for a brand or query.

### `get_transactions`

Retrieve transactions with optional advertiser and date filtering.

## Example direct usage

```bash
python3 example_usage.py
```

## Testing

```bash
python3 -m unittest test_hienergy_client.py -v
```

## Suggested next steps

- Add OAuth if this will be connected in a shared ChatGPT workspace
- Add richer tool annotations or write actions once the read-only flow is working
- Deploy behind a stable HTTPS endpoint for ChatGPT import
