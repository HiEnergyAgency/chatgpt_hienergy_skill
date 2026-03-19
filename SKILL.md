---
name: hienergy-chatgpt-app
description: >-
  Build and operate a ChatGPT-compatible HiEnergy app backed by a remote MCP
  server. Use this skill when you need to expose HiEnergy advertisers,
  affiliate programs, deals, contacts, and transaction lookups to ChatGPT or
  the OpenAI Responses API. Includes a FastMCP server, a reusable HiEnergy API
  client, local setup instructions, and deployment guidance for private
  workspace use.
homepage: https://www.hienergy.ai
metadata: {"openclaw":{"homepage":"https://www.hienergy.ai","requires":{"env":["HIENERGY_API_KEY"]},"primaryEnv":"HIENERGY_API_KEY"}}
---

# HiEnergy ChatGPT App

Use this repository as a ChatGPT app version of the existing HiEnergy OpenClaw skill.

## Overview

- The repo exposes HiEnergy data to ChatGPT through a remote MCP server.
- The server is read-only by default and focuses on advertiser discovery, affiliate programs, deals, contacts, and transaction lookups.
- ChatGPT handles the natural-language layer; the MCP tools return structured data.

## Architecture

1. `scripts/hienergy_client.py` talks to the HiEnergy API with `HIENERGY_API_KEY`.
2. `scripts/hienergy_chatgpt_server.py` wraps that client with FastMCP tools.
3. ChatGPT or the Responses API connects to the server over an SSE endpoint at `/sse`.

## Tool Design

- `search_advertisers` for name, domain, and URL lookup
- `get_advertiser_profile` for deeper advertiser details
- `search_affiliate_programs` for commission-focused program lookup
- `find_deals` for active offers and market filters
- `search_contacts` for partner discovery
- `get_transactions` for light reporting and analytics

## Setup

```bash
cp .env.example .env
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export HIENERGY_API_KEY="<your_api_key>"
python3 scripts/hienergy_chatgpt_server.py
```

Python 3.10+ is recommended because the FastMCP dependency does not install on Python 3.9.

For ChatGPT, expose the local server through a public HTTPS URL and use the `/sse` path when connecting.

## Security

- Keep `HIENERGY_API_KEY` in local environment variables only.
- This scaffold is intended for private/internal use first.
- Add OAuth before production rollout to a broader ChatGPT workspace.

## Resources

- `README.md` for repo-level setup and usage
- `references/chatgpt_mcp_setup.md` for ChatGPT connection notes
- `test_hienergy_client.py` for client validation
