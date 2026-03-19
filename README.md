# HiEnergy ChatGPT App

This repository is a ChatGPT-oriented version of the existing HiEnergy OpenClaw skill.

Instead of packaging the capability as an OpenClaw skill, this repo exposes HiEnergy data through a remote MCP server so ChatGPT can call it as an app or through the OpenAI Responses API.

## What it includes

- A reusable HiEnergy API client in `scripts/hienergy_client.py`
- A FastMCP server in `scripts/hienergy_chatgpt_server.py`
- Read-only tools for advertisers, affiliate programs, deals, contacts, and transactions
- Setup notes for local development and ChatGPT connection
- Unit tests for the API client

## Quick start

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

The server starts on `http://0.0.0.0:8000` by default and exposes the MCP SSE transport from the FastMCP runtime.

## Connecting to ChatGPT

1. Expose the local server over HTTPS, for example with a tunnel or deployment target.
2. Use the public URL ending in `/sse/`.
3. Import that server into ChatGPT as a custom MCP app.

This repo keeps all tools read-only so it is safe to test before adding any write actions.

## Render deployment

This repo includes `render.yaml` for a simple web-service deploy on Render.

- The service starts even if `HIENERGY_API_KEY` is not configured yet.
- Tool calls will fail with a clear error until you add that secret in Render.
- The expected ChatGPT connection URL is your deployed base URL plus `/sse/`.

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
