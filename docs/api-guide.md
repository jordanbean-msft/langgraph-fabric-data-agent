---
title: API Guide
description: How to integrate with and call the LangGraph MCP REST API sample
ms.date: 2026-04-02
---

## Overview

The `langgraph-fabric-api` package is a standalone FastAPI server that exposes one or more MCP-backed tools, or plain chat-only mode, over HTTP. Your application authenticates its users and streams the agent's response back using Server-Sent Events (SSE).

This guide is for **developers building applications** that integrate with this API. The examples use Microsoft Fabric as a concrete MCP backend.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Entra ID app registration for the API server and a separate calling app registration for your local client. See the [API server app registration section](app-registration.md#api-server-app-registration) and [calling app registration for API examples](app-registration.md#calling-app-registration-for-api-examples).
- A `.env` file in `packages/langgraph-fabric-api/` with the required server-side environment variables (see [Environment variables](#environment-variables) below).

## Authentication overview

The authentication flow has two halves: one handled by your **client application** and one handled by the **API server** internally.

```
Client App          API Server           Microsoft Entra ID       MCP Server
    │                    │                       │                       │
    │ 1. Auth Code flow  │                       │                       │
    │──────────────────────────────────────────>│                       │
    │ 2. User JWT        │                       │                       │
    │<──────────────────────────────────────────│                       │
    │                    │                       │                       │
    │ 3. POST /chat/stream                       │                       │
    │   Authorization: Bearer <user-jwt>         │                       │
    │──────────────────>│                        │                       │
    │                    │ 4. OBO exchange        │                       │
    │                    │──────────────────────>│                       │
    │                    │ 5. Scope-specific token│                       │
    │                    │<──────────────────────│                       │
    │                    │                        │  6. MCP call with    │
    │                    │──────────────────────────────────────────────>│
    │                    │<──────────────────────────────────────────────│
    │ 7. SSE stream      │                        │                       │
    │<──────────────────│                         │                       │
```

### Client side: OAuth 2.0 Authorization Code flow

Your calling application authenticates the end user with the **OAuth 2.0 Authorization Code flow** against Microsoft Entra ID. The access token audience must be this API server's app registration, not the Fabric API directly. Use the [Microsoft Authentication Library (MSAL)](https://learn.microsoft.com/entra/identity-platform/msal-overview) or any OIDC-compliant library.

Request the API server's delegated scope:

```
api://<YOUR_API_CLIENT_ID>/access_as_user
```

That configuration lives on the public calling app registration described in [calling app registration for API examples](app-registration.md#calling-app-registration-for-api-examples).

Your application then includes the resulting JWT in every request to this API:

```
Authorization: Bearer <user-jwt>
```

### Server side: On-Behalf-Of (OBO) flow

The API server validates the incoming JWT on every request. If MCP servers are configured, it also performs an [On-Behalf-Of exchange](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow) internally to obtain an access token for each configured MCP server scope:

1. The server uses its own confidential client credentials, `MICROSOFT_APP_ID` and `MICROSOFT_APP_PASSWORD`, to call Entra ID.
2. The incoming user JWT is supplied as `user_assertion`.
3. Entra ID returns a new token for the configured server scope, for example `https://api.fabric.microsoft.com/.default`.
4. That server token is forwarded to the matching MCP server. The caller never sees it.

### Entra ID registrations used by this flow

This flow uses two separate registrations.

| Registration | Client type | Purpose |
| --- | --- | --- |
| API server app registration | Confidential client | Accepts the caller's token and performs the OBO exchange |
| Calling app registration | Public client | Signs the user in and requests the API server scope |

For the API server app registration, configure these values:

| Setting | Value |
| --- | --- |
| Application ID URI | `api://<YOUR_API_CLIENT_ID>` |
| Exposed API scope | `access_as_user` |
| Client secret | Required, stored in `MICROSOFT_APP_PASSWORD` |
| Environment variables | `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_TENANT_ID` |

For the calling app registration, configure these values:

| Setting | Value |
| --- | --- |
| Platform | Mobile and desktop applications |
| Redirect URI for notebook example | `http://localhost` |
| Redirect URI for REST Client example | `http://localhost:3000/callback` |
| Delegated permission | `api://<YOUR_API_CLIENT_ID>/access_as_user` |
| Recommended trust configuration | Add the caller app as an authorized client application on the API server registration |

See the [app registration guide](app-registration.md) for the full walkthrough.

## Start the server

```bash
uv run langgraph-fabric-api
```

The server starts on port `8000` by default. Override with `PORT=<number>` in `.env`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `POST` | `/chat/stream` | Submit a prompt and stream the agent response |

## Request schema

`POST /chat/stream`

**Required header:**

```
Authorization: Bearer <user-jwt>
```

**Request body:**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `prompt` | `string` | Yes | The user's question or instruction |

**Example request body:**

```json
{
  "prompt": "What are the top 10 sales by region?"
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

The current sample always requires an `Authorization` header on `POST /chat/stream`, even if `MCP_SERVERS` is empty and the request will run in chat-only mode.

## Example: Python client using `httpx`

```python
import httpx

url = "http://localhost:8000/chat/stream"
headers = {
    "Authorization": f"Bearer {user_token}",  # JWT obtained via auth code flow
    "Content-Type": "application/json",
}

with httpx.Client(timeout=120) as client:
    with client.stream("POST", url, json={"prompt": "What are the top 10 sales by region?"}, headers=headers) as response:
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


async def stream_chat(prompt: str, user_token: str) -> None:
    url = "http://localhost:8000/chat/stream"
    headers = {
        "Authorization": f"Bearer {user_token}",  # JWT obtained via auth code flow
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"prompt": prompt}, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                text = line.decode().strip()
                if text.startswith("data:"):
                    chunk = text[len("data:"):].strip()
                    if chunk == "[DONE]":
                        break
                    print(chunk, end="", flush=True)


asyncio.run(stream_chat("What are the top 10 sales by region?", user_token))
```

## Example: JavaScript / TypeScript client using `fetch`

```typescript
async function streamChat(prompt: string, userToken: string): Promise<void> {
  const response = await fetch("http://localhost:8000/chat/stream", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${userToken}`, // JWT obtained via auth code flow
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt }),
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

streamChat("What are the top 10 sales by region?", userToken);
```

## Example: `curl`

```bash
curl -s -N \
  -X POST http://localhost:8000/chat/stream \
  -H "Authorization: Bearer <user-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the top 10 sales by region?"}' \
| while IFS= read -r line; do
    [[ "$line" == "data: [DONE]" ]] && break
    [[ "$line" == data:* ]] && printf '%s' "${line#data: }"
  done
```

## Environment variables

All settings are read from `packages/langgraph-fabric-api/.env` via the API settings model. The following variables are required to run the API server:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `MCP_SERVERS` | Yes | — | JSON array of MCP servers with `name`, `description`, `url`, `scope`, `oauth_connection_name`, `timeout_seconds`, `poll_interval_seconds` |
| `MICROSOFT_APP_ID` | Yes | — | Client ID of the API server's Entra app registration |
| `MICROSOFT_APP_PASSWORD` | Yes | — | Client secret for the OBO exchange |
| `MICROSOFT_TENANT_ID` | Yes | — | Entra tenant ID |
| `PORT` | No | `8000` | Port the server listens on |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [packages/langgraph-fabric-api/.env.example](../packages/langgraph-fabric-api/.env.example) for a full template.

