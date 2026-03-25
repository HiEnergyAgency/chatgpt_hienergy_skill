# ChatGPT MCP Setup Notes

HiEnergy now exposes a hosted MCP endpoint at `https://app.hienergy.ai/mcp`.

Use the hosted server for production ChatGPT, Codex, and Responses API integrations. The local FastMCP server in this repo still exists for development and exposes `/mcp`.

## Hosted flow

1. Generate a ChatGPT-ready server URL in the form `https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY`.
2. In ChatGPT Developer Mode, add a remote MCP server using that full URL.
3. Choose `No Authentication` because the URL already contains the API key.
4. In Codex, run `codex mcp add hienergy --url "https://app.hienergy.ai/mcp?api_key=YOUR_API_KEY"`.
5. For lower-level MCP clients, send JSON-RPC requests to `/mcp` and authenticate with `X-Api-Key`.

## Local flow

1. Use Python 3.10+ and install dependencies from `requirements.txt`.
2. Export `HIENERGY_API_KEY`.
3. Run `python3 scripts/hienergy_chatgpt_server.py`.
4. Expose the running server through a public HTTPS URL.
5. Connect ChatGPT to the public `/mcp` URL if you are testing the local scaffold.

## Production notes

- The hosted HiEnergy MCP server now exposes a broader authenticated tool set, discovery resources, and a generic `api_request` bridge.
- The local scaffold mirrors a broad subset of that surface and also exposes `/mcp`.
- Prefer OAuth for shared or production deployments when you move beyond the current API-key flow.
- Return structured JSON-like payloads from tools and let ChatGPT handle the natural-language response.

## Deployment ideas

- Replit
- Render
- Railway
- Fly.io
- Any HTTPS host that can expose the FastMCP HTTP `/mcp` endpoint
