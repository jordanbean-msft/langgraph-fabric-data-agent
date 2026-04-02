---
title: API Guide
description: How to authenticate and call the LangGraph Fabric Data Agent streaming API
ms.date: 2026-04-01
---

# API Guide

The `langgraph-fabric-api` package exposes a FastAPI server with a Server-Sent Events streaming endpoint for querying the Fabric Data Agent. This guide covers authentication setup and how to call the endpoint from client code.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/chat/stream` | Stream agent responses as Server-Sent Events |

> [!NOTE]
> The API endpoints are intentionally unauthenticated in this sample. All authentication is performed internally against Azure OpenAI and the Fabric Data Agent MCP endpoint.

## Authentication

The API server itself does not require callers to authenticate. However, the underlying Fabric Data Agent calls always require a user identity. The `auth_mode` field in the request body controls how that token is obtained.

### `auth_mode: "local"` (default)

In local mode the server acquires a Fabric token using `DefaultAzureCredential`, falling back to an interactive device-code flow if ambient credentials are unavailable.

**Setup:**

1. Sign in with the Azure CLI before starting the server:

   ```bash
   az login
   ```

2. Ensure your signed-in account has the required Fabric permissions listed in the [app registration guide](app-registration.md).

3. Start the API server:

   ```bash
   uv run langgraph-fabric-api
   ```

4. Send requests without a `fabric_user_token` (or leave it `null`):

   ```json
   {
     "prompt": "What are the top 10 sales by region?",
     "user_id": "alice@example.com",
     "auth_mode": "local"
   }
   ```

The server calls `DefaultAzureCredential.get_token` for the scope defined in `FABRIC_DATA_AGENT_SCOPE` (default: `https://api.fabric.microsoft.com/.default`).

### `auth_mode: "hosted"` (Bot Service token)

In hosted mode the caller supplies a Bot Service user token obtained via the M365 Agents SDK OAuth flow. This is used internally by the `langgraph-fabric-m365` adapter and is not normally called directly.

```json
{
  "prompt": "What are the top 10 sales by region?",
  "user_id": "alice@example.com",
  "auth_mode": "hosted",
  "fabric_user_token": "<bot-service-user-token>"
}
```

The `fabric_user_token` value must be a delegated access token for the Fabric API scope (`https://api.fabric.microsoft.com/.default`) obtained through the Azure Bot Service OAuth connection.

## Request schema

`POST /chat/stream`

```json
{
  "prompt": "string (required) — the user's question or instruction",
  "user_id": "string (optional, default: \"local-user\") — identifier for the requesting user",
  "auth_mode": "string (optional, default: \"local\") — \"local\" or \"hosted\"",
  "fabric_user_token": "string | null (optional) — required when auth_mode is \"hosted\""
}
```

## Response format

The endpoint returns a `text/event-stream` response (Server-Sent Events).

Each streamed chunk is a plain-text data frame:

```
data: <chunk text>\n\n
```

When the agent has finished, a terminal event is sent:

```
event: done
data: [DONE]
```

Chunks contain partial LLM output tokens and may also include tool call progress messages, depending on the graph state. Consumers should concatenate `data:` payloads until the `done` event is received.

## Example: Python client using `httpx`

```python
import httpx

url = "http://localhost:8000/chat/stream"
payload = {
    "prompt": "What are the top 10 sales by region?",
    "user_id": "alice@example.com",
    "auth_mode": "local",
}

with httpx.Client(timeout=120) as client:
    with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data:"):
                chunk = line[len("data:"):].strip()
                if chunk == "[DONE]":
                    break
                print(chunk, end="", flush=True)
```

## Example: Python client using `aiohttp`

```python
import aiohttp
import asyncio

async def stream_chat(prompt: str) -> None:
    url = "http://localhost:8000/chat/stream"
    payload = {
        "prompt": prompt,
        "user_id": "alice@example.com",
        "auth_mode": "local",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                text = line.decode().strip()
                if text.startswith("data:"):
                    chunk = text[len("data:"):].strip()
                    if chunk == "[DONE]":
                        break
                    print(chunk, end="", flush=True)

asyncio.run(stream_chat("What are the top 10 sales by region?"))
```

## Example: JavaScript / TypeScript client using `fetch`

```typescript
async function streamChat(prompt: string): Promise<void> {
  const response = await fetch("http://localhost:8000/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      user_id: "alice@example.com",
      auth_mode: "local",
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value, { stream: true });
    for (const line of text.split("\n")) {
      if (line.startsWith("data:")) {
        const chunk = line.slice("data:".length).trim();
        if (chunk === "[DONE]") return;
        process.stdout.write(chunk);
      }
    }
  }
}

streamChat("What are the top 10 sales by region?");
```

## Example: `curl`

```bash
curl -s -N \
  -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the top 10 sales by region?", "auth_mode": "local"}' \
| while IFS= read -r line; do
    [[ "$line" == "data: [DONE]" ]] && break
    [[ "$line" == data:* ]] && printf '%s' "${line#data: }"
  done
```

## Environment variables

The API server reads all settings from `.env` via `langgraph_fabric_core/core/config.py`.
Ensure these are set before starting the server:

| Variable | Purpose |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Chat model deployment name (e.g. `gpt-5.4`) |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2025-11-15-preview`) |
| `FABRIC_DATA_AGENT_MCP_URL` | Fabric Data Agent MCP endpoint URL |
| `FABRIC_DATA_AGENT_SCOPE` | OAuth scope for Fabric (default: `https://api.fabric.microsoft.com/.default`) |
| `FABRIC_DATA_AGENT_TIMEOUT_SECONDS` | MCP call timeout (default: `120`) |
| `PORT` | Listening port (default: `8000`) |
| `LOG_LEVEL` | Root log level (default: `INFO`) |

See [.env.example](../.env.example) for a full template.
