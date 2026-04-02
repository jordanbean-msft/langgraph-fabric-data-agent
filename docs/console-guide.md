---
title: Console Guide
description: How to set up and use the LangGraph MCP interactive terminal sample
ms.date: 2026-04-01
---

# Console Guide

The `langgraph-fabric-console` package is an interactive terminal client for MCP-backed tools or chat-only mode. It streams the agent's response to `stdout` as tokens arrive and maintains multi-turn conversation history within a session.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- If you configure MCP servers, an Azure CLI session (`az login`) or another supported credential with access to the configured backend. For Fabric examples, use the permissions described in the [app registration guide](app-registration.md).
- A `.env` file in `packages/langgraph-fabric-console/` with the required environment variables (see [Environment variables](#environment-variables) below).

## Authentication setup

If you configure MCP servers, the console uses [`DefaultAzureCredential`](https://learn.microsoft.com/azure/developer/python/sdk/authentication-overview) to acquire an access token for the configured MCP server scope. Before running the console, ensure one of the following credential sources is active:

| Credential source | How to configure |
| --- | --- |
| Azure CLI | `az login` — simplest option for local development |
| Managed Identity | Assign the managed identity the roles or permissions required by the configured MCP backend |
| Workload Identity | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_FEDERATED_TOKEN_FILE` in the environment |
| Service Principal (secret) | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` in the environment |

The account or identity must have the permissions required by the configured MCP backend. For Fabric examples, use the delegated permissions listed in the [app registration guide](app-registration.md).

If no ambient credential is available, the runtime falls back to an interactive device-code flow.

If `MCP_SERVERS` is empty or omitted, the console runs in chat-only mode and does not attempt MCP authentication.

## Start the console

```bash
az login          # needed only when MCP-backed tool calls are enabled
uv run langgraph-fabric-console
```

You will see:

```
LangGraph MCP console. Press Enter on empty input to exit.
You:
```

## Usage

Type your prompt at the `You:` prompt and press **Enter**. The agent streams its response back to the terminal as it is generated. Press **Enter** on an empty line to end the session.

```
You: What are the top 10 sales by region?
Assistant: Here are the top 10 sales by region based on the MCP data:
...
You:
```

Conversation history is maintained for the duration of the terminal session. Each exchange is appended to the in-memory history and passed back to the agent on the next turn, enabling follow-up questions.

> [!NOTE]
> History resets when you exit the console. There is no persistence between sessions in this sample.

## Environment variables

All settings are read from `packages/langgraph-fabric-console/.env` via the console settings model. The following variables are required to run the console:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `MCP_SERVERS` | No | `[]` | JSON array of MCP servers with `name`, `description`, `url`, `scope`, `oauth_connection_name`, `timeout_seconds`, `poll_interval_seconds` |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [packages/langgraph-fabric-console/.env.example](../packages/langgraph-fabric-console/.env.example) for a full template.
