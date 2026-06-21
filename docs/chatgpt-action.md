# Run the router from a normal ChatGPT window

A normal ChatGPT conversation cannot run this repository's local Python CLI directly. To use the router from ChatGPT, expose the router as an HTTPS API and connect it to a Custom GPT Action.

OpenAI's GPT Actions documentation says actions connect a GPT to an external API using authentication plus an OpenAPI schema. Build and edit GPTs from the GPTs area in ChatGPT, then add an action in the GPT editor.

## 1. Run the API locally

```bash
cd /workspace/Token-router-optimization
python -m pip install -e .[server,pdf]
export OPENAI_API_KEY="your_api_key"
uvicorn token_router.server:app --host 0.0.0.0 --port 8000
```

## 2. Expose it over HTTPS

For local testing, use a tunnel such as ngrok or Cloudflare Tunnel:

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL, for example `https://abc123.ngrok.app`.

## 3. Add it to a Custom GPT

1. Open ChatGPT in a browser.
2. Go to **Explore GPTs** → **Create**.
3. Open **Configure** → **Actions** → **Create new action**.
4. Set authentication to your preferred API-key option if you protect the service, or `None` for private local tunnel testing.
5. Import the OpenAPI schema from `https://YOUR_HOST/openapi.json`.
6. Save and test the action in the GPT preview.

## 4. How to use PDFs in ChatGPT

ChatGPT attachments are not automatically mounted into this repository's local filesystem. Use one of these approaches:

- Ask ChatGPT to read the attached PDF and call the action with extracted `source_text`.
- Have the GPT send a base64-encoded PDF as `pdf_base64` when that is practical for small PDFs.
- Upload the PDF to your own storage, extract text in your service, and pass `source_text` to `/execute`.

For large PDFs, `source_text` or server-side file storage is more reliable than base64 in an action call.

## 5. Example action request

```json
{
  "task": "summarize the easy findings, then produce a rigorous risk analysis",
  "source_text": "Paste extracted PDF text here...",
  "compare_baseline": true,
  "execute": true
}
```

The response includes the route plan, optional baseline comparison, final analysis, actual API token usage, latency, and estimated cost.
