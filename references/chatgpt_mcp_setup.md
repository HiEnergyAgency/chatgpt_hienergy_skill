# ChatGPT MCP Setup Notes

This repo uses a remote MCP server pattern so ChatGPT can call HiEnergy tools over a public SSE endpoint.

## Local flow

1. Use Python 3.10+ and install dependencies from `requirements.txt`.
2. Export `HIENERGY_API_KEY`.
3. Run `python3 scripts/hienergy_chatgpt_server.py`.
4. Expose the running server through a public HTTPS URL.
5. Connect ChatGPT to the public `/sse/` URL.

## Production notes

- Keep the current tool set read-only until you are comfortable with the flow.
- Prefer OAuth for shared or production deployments.
- Return structured JSON-like payloads from tools and let ChatGPT handle the natural-language response.

## Deployment ideas

- Replit
- Render
- Railway
- Fly.io
- Any HTTPS host that can expose the FastMCP SSE endpoint
