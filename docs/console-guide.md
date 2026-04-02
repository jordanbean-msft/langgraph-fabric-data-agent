---
title: Console Guide
description: How to set up and use the LangGraph Fabric Data Agent interactive terminal
ms.date: 2026-04-01
---

# Console Guide

The `langgraph-fabric-console` package is an interactive terminal client for the Fabric Data Agent. It streams the agent's response to `stdout` as tokens arrive and maintains multi-turn conversation history within a session.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/) installed.
- An Azure CLI session (`az login`) with an account that has the Fabric permissions described in the [app registration guide](app-registration.md).
- A `.env.console` file at the repository root with the required environment variables (see [Environment variables](#environment-variables) below).

## Authentication setup

The console uses [`DefaultAzureCredential`](https://learn.microsoft.com/azure/developer/python/sdk/authentication-overview) to acquire a Fabric token on behalf of the signed-in user. Before running the console, ensure one of the following credential sources is active:

| Credential source | How to configure |
| --- | --- |
| Azure CLI | `az login` — simplest option for local development |
| Managed Identity | Assign the managed identity the required Fabric roles; no additional configuration needed |
| Workload Identity | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_FEDERATED_TOKEN_FILE` in the environment |
| Service Principal (secret) | Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` in the environment |

The account or identity must have the Fabric delegated permissions listed in the [app registration guide](app-registration.md).

If no ambient credential is available, the runtime falls back to an interactive device-code flow.

## Start the console

```bash
az login          # authenticate so DefaultAzureCredential can acquire a Fabric token
uv run langgraph-fabric-console
```

You will see:

```
LangGraph Fabric MCP console. Press Enter on empty input to exit.
You:
```

## Usage

Type your prompt at the `You:` prompt and press **Enter**. The agent streams its response back to the terminal as it is generated. Press **Enter** on an empty line to end the session.

```
You: What are the top 10 sales by region?
Assistant: Here are the top 10 sales by region based on the Fabric data:
...
You:
```

Conversation history is maintained for the duration of the terminal session. Each exchange is appended to the in-memory history and passed back to the agent on the next turn, enabling follow-up questions.

> [!NOTE]
> History resets when you exit the console. There is no persistence between sessions in this sample.

## Environment variables

All settings are read from `.env.console` via the console settings model. The following variables are required to run the console:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI / Foundry project endpoint |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Yes | — | Chat model deployment name (e.g. `gpt-4o`) |
| `AZURE_OPENAI_API_VERSION` | No | `2025-11-15-preview` | Azure OpenAI API version |
| `FABRIC_DATA_AGENT_MCP_URL` | Yes | — | Fabric Data Agent MCP endpoint URL |
| `FABRIC_DATA_AGENT_SCOPE` | No | `https://api.fabric.microsoft.com/.default` | OAuth scope used to acquire the Fabric token |
| `FABRIC_DATA_AGENT_TIMEOUT_SECONDS` | No | `120` | Maximum seconds to wait for an MCP response |
| `LOG_LEVEL` | No | `INFO` | Root log level |

See [.env.console.example](../.env.console.example) for a full template.
