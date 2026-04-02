---
title: API Guide
description: How to integrate with and call the LangGraph Fabric Data Agent REST API
ms.date: 2026-04-01
---

# API Guide

The `langgraph-fabric-api` package is a standalone FastAPI server that exposes the Fabric Data Agent over HTTP. It accepts a text prompt and a delegated user token, then streams the agent's response back to the caller using Server-Sent Events (SSE).

This guide is for **developers building applications** that integrate with the Fabric Data Agent API. Your application is responsible for authenticating the end user and obtaining a Fabric-scoped access token, which is then forwarded to the API with each request.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Entra ID app registration for your client application with the Fabric API permission — see the [app registration guide](app-registration.md).
- A `.env` file at the repository root with the required server-side environment variables (see [Environment variables](#environment-variables) below).

## Authentication

The API itself is **unauthenticated at the transport layer** (no bearer token is required to reach the `/chat/stream` endpoint). Authentication is instead user-delegated: your application acquires a Fabric access token on behalf of the signed-in user and passes it in the request body.

### How it works

1. **Your application** authenticates the end user with the **OAuth 2.0 Authorization Code flow** against Microsoft Entra ID (Azure AD).
2. **Your application** requests an access token with the Fabric API scope (`https://api.fabric.microsoft.com/.default`). If your backend receives a token for your own API audience, use the [On-Behalf-Of (OBO) flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow) to exchange it for a Fabric-scoped token.
3. **Your application** passes the resulting `fabric_user_token` to every `/chat/stream` call.
4. **The API** forwards that token directly to the Fabric Data Agent MCP endpoint — no server-side credential is needed.

### Entra ID app registration

Register a client application in Entra ID with the following settings:

| Property | Value |
| --- | --- |
| Supported account types | Single tenant (`AzureADMyOrg`) or multi-tenant as needed |
| Platform | Web, SPA, or mobile/desktop depending on your client type |
| Redirect URI | Your application's OAuth callback URI |
| API permission | `Delegated` — `https://api.fabric.microsoft.com/` → `Item.Read.All` (or the Fabric scope required by your Data Agent) |

Grant admin consent for the Fabric API permission so users are not prompted individually.

> [!NOTE]
> The same Entra app used for the M365 / Teams integration can be reused here if it already has Fabric delegated permissions. See the [app registration guide](app-registration.md) for the full permission list.

### Acquiring the token (Authorization Code flow)

Use the [Microsoft Authentication Library (MSAL)](https://learn.microsoft.com/entra/identity-platform/msal-overview) or any OIDC-compliant library in your client application. The scope to request is:

```
https://api.fabric.microsoft.com/.default
```

Or, if using OBO from your own API backend:

```python
# MSAL Python — On-Behalf-Of flow
app = msal.ConfidentialClientApplication(
    client_id="<YOUR_CLIENT_ID>",
    client_credential="<YOUR_CLIENT_SECRET>",
    authority="https://login.microsoftonline.com/<YOUR_TENANT_ID>",
)
result = app.acquire_token_on_behalf_of(
    user_assertion=incoming_user_token,
    scopes=["https://api.fabric.microsoft.com/.default"],
)
fabric_user_token = result["access_token"]
```

## Start the server

```bash
uv run langgraph-fabric-api
```

The server starts on port `8000` by default. Override it with `PORT=<number>` in `.env`.

> [!NOTE]
> While user authentication is fully delegated to the calling application (no `az login` is needed), the server still requires Azure OpenAI credentials and the Fabric MCP URL to be configured in `.env`. See [Environment variables](#environment-variables) below.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/chat/stream` | Submit a prompt and stream the agent response |

## Request schema

`POST /chat/stream`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `prompt` | `string` | Yes | — | The user's question or instruction |
| `fabric_user_token` | `string` | No | `null` | Fabric-scoped access token obtained by your application on behalf of the user. When provided, the token is forwarded directly to the Fabric Data Agent and the user identity is extracted from the JWT claims for log correlation. |

**Example request body:**

```json
{
  "prompt": "What are the top 10 sales by region?",
  "fabric_user_token": "<fabric-scoped-access-token>"
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
    "fabric_user_token": fabric_user_token,  # obtained via auth code / OBO flow
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


async def stream_chat(prompt: str, fabric_user_token: str) -> None:
    url = "http://localhost:8000/chat/stream"
    payload = {
        "prompt": prompt,
        "fabric_user_token": fabric_user_token,  # obtained via auth code / OBO flow
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


asyncio.run(stream_chat("What are the top 10 sales by region?", fabric_user_token))
# fabric_user_token is obtained via your application's auth code / OBO flow
```

## Example: JavaScript / TypeScript client using `fetch`

```typescript
async function streamChat(prompt: string, fabricUserToken: string): Promise<void> {
  const response = await fetch("http://localhost:8000/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      fabric_user_token: fabricUserToken, // obtained via auth code / OBO flow
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

streamChat("What are the top 10 sales by region?", fabricUserToken);
// fabricUserToken is obtained via your application's auth code / OBO flow
```

## Example: `curl`

```bash
curl -s -N \
  -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the top 10 sales by region?",
    "fabric_user_token": "<fabric-scoped-access-token>"
  }' \
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
| `FABRIC_DATA_AGENT_SCOPE` | No | `https://api.fabric.microsoft.com/.default` | OAuth scope the client should request |
| `FABRIC_DATA_AGENT_TIMEOUT_SECONDS` | No | `120` | Maximum seconds to wait for an MCP response |
| `PORT` | No | `8000` | Port the server listens on |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [.env.example](../.env.example) for a full template.
