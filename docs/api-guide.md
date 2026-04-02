---
title: API Guide
description: How to set up and call the LangGraph Fabric Data Agent REST API
ms.date: 2026-04-01
---

# API Guide

The `langgraph-fabric-api` package is a standalone FastAPI server that exposes the Fabric Data Agent over HTTP. It accepts a text prompt and streams the agent's response back to the caller using Server-Sent Events (SSE).

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Azure CLI session (`az login`) with an account that has the Fabric permissions described in the [app registration guide](app-registration.md).
- A `.env` file at the repository root with the required environment variables (see [Environment variables](#environment-variables) below).

## Start the server

```bash
az login          # authenticate so DefaultAzureCredential can acquire a Fabric token
uv run langgraph-fabric-api
```

The server starts on port `8000` by default. Override it with `PORT=<number>` in `.env`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/chat/stream` | Submit a prompt and stream the agent response |

> [!NOTE]
> The API endpoints are intentionally unauthenticated in this sample. Authentication is performed internally — the server acquires a Fabric access token using `DefaultAzureCredential` on behalf of the process identity (your `az login` session, a managed identity, or a workload identity).

## Authentication setup

The server uses [`DefaultAzureCredential`](https://learn.microsoft.com/azure/developer/python/sdk/authentication-overview) to obtain a delegated Fabric token. Before making API calls, ensure one of the following credential sources is available:

| Credential source | How to configure |
| --- | --- |
| Azure CLI | `az login` — simplest option for local development |
| Managed Identity | Assign the managed identity the required Fabric roles; no additional configuration needed |
| Workload Identity | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_FEDERATED_TOKEN_FILE` in the environment |
| Service Principal (secret) | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` in the environment |

The account or identity must have the Fabric delegated permissions listed in the [app registration guide](app-registration.md).

If no ambient credential is available, the server falls back to an interactive device-code flow.

## Request schema

`POST /chat/stream`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `prompt` | `string` | Yes | — | The user's question or instruction |
| `user_id` | `string` | No | `"local-user"` | An identifier for the requesting user, used for correlation logging |

**Example request body:**

```json
{
  "prompt": "What are the top 10 sales by region?",
  "user_id": "alice@example.com"
}
```

## Response format

The endpoint returns a `text/event-stream` (SSE) response. Each chunk from the agent is delivered as a data frame:

```
data: <chunk text>

```

When the agent finishes, a terminal event is emitted:

```
event: done
data: [DONE]

```

Chunks contain partial LLM output tokens and may also include tool-call progress messages. Concatenate all `data:` payloads until the `done` event is received to assemble the full response.

## Example: Python client using `httpx`

```python
import httpx

url = "http://localhost:8000/chat/stream"
payload = {
    "prompt": "What are the top 10 sales by region?",
    "user_id": "alice@example.com",
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
import asyncio
import aiohttp


async def stream_chat(prompt: str) -> None:
    url = "http://localhost:8000/chat/stream"
    payload = {
        "prompt": prompt,
        "user_id": "alice@example.com",
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
  -d '{"prompt": "What are the top 10 sales by region?", "user_id": "alice@example.com"}' \
| while IFS= read -r line; do
    [[ "$line" == "data: [DONE]" ]] && break
    [[ "$line" == data:* ]] && printf '%s' "${line#data: }"
  done
```

## Environment variables

All settings are read from `.env` via the core settings model. The following variables are required to run the API server:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `FABRIC_DATA_AGENT_MCP_URL` | Yes | — | Fabric Data Agent MCP endpoint URL |
| `FABRIC_DATA_AGENT_SCOPE` | No | `https://api.fabric.microsoft.com/.default` | OAuth scope used to acquire the Fabric token |
| `FABRIC_DATA_AGENT_TIMEOUT_SECONDS` | No | `120` | Maximum seconds to wait for an MCP response |
| `PORT` | No | `8000` | Port the server listens on |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [.env.example](../.env.example) for a full template.
