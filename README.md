---
title: LangGraph Fabric Data Agent Sample
description: Python monorepo sample showing a LangGraph agent calling a Fabric Data Agent through MCP, structured as independent packages for core logic and each client interface
ms.date: 2026-04-01
---

## Overview

This repository demonstrates a LangGraph-based AI agent that calls a Fabric Data Agent via MCP.

The sample is organized as a **uv workspace** with four independent Python packages:

| Package | Description |
| --- | --- |
| [`langgraph-fabric-core`](packages/langgraph-fabric-core/) | Interface-agnostic: graph, orchestrator, Fabric MCP client, auth, LLM factory |
| [`langgraph-fabric-api`](packages/langgraph-fabric-api/) | FastAPI streaming endpoint |
| [`langgraph-fabric-console`](packages/langgraph-fabric-console/) | Interactive terminal with streamed responses |
| [`langgraph-fabric-m365`](packages/langgraph-fabric-m365/) | Teams / Copilot Chat via M365 Agents SDK |

`langgraph-fabric-core` has **no** dependency on FastAPI, aiohttp, or the M365 Agents SDK. Each interface package depends only on core.

See [docs/architecture.md](docs/architecture.md) for a detailed breakdown of each module.

## Prerequisites

Base prerequisites:

- Python 3.12 or later
- `uv`
- Azure CLI 2.55.0 or later
- Access to an Azure OpenAI / Foundry project with a `gpt-5.4` deployment
- Access to a Fabric Data Agent MCP endpoint
- A signed-in user account that can authenticate to Azure and Fabric

M365 adapter prerequisites (Teams / Copilot Chat only):

- A Microsoft Entra app registration for the bot — see [docs/app-registration.md](docs/app-registration.md)
- An Azure Bot resource with a Bot Service OAuth connection — see [docs/azure-bot-service.md](docs/azure-bot-service.md)
- Access to a Microsoft 365 tenant where you can test in Teams or Copilot Chat

Optional local tooling:

- `devtunnel` CLI for exposing the M365 adapter from your machine
- `zip` for the `build-m365-app-package` task

## Setup

1. Install all workspace packages and dev dependencies:

```bash
uv sync --all-packages --extra dev
```

2. Copy the environment file for your target interface and fill your values:

```bash
# Console
cp .env.console.example .env.console

# FastAPI server
cp .env.api.example .env.api

# M365 adapter (Teams / Copilot Chat)
cp .env.m365.example .env.m365
```

3. Fill the Azure OpenAI and Fabric MCP values in the copied file.
4. For the M365 adapter, also set `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_TENANT_ID`, `FABRIC_OAUTH_CONNECTION_NAME`, and the `CONNECTIONS__SERVICE_CONNECTION__*` values from the [app registration reference](docs/app-registration.md).

## Run

API surface:

```bash
uv run langgraph-fabric-api
```

Console surface:

```bash
uv run langgraph-fabric-console
```

M365 adapter (Teams / Copilot Chat):

```bash
uv run langgraph-fabric-m365
```

## Validate

```bash
uv run ruff check .
uv run pytest
```

## Documentation

| Guide | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Per-package module breakdown and dependency rules |
| [docs/api-guide.md](docs/api-guide.md) | API authentication setup and streaming endpoint usage |
| [docs/console-guide.md](docs/console-guide.md) | Console authentication setup and interactive terminal usage |
| [docs/m365-guide.md](docs/m365-guide.md) | Teams and Copilot Chat M365 adapter setup, OAuth sign-in flow, and environment reference |
| [docs/app-registration.md](docs/app-registration.md) | Entra app registration reference, API permissions, and environment variable mapping |
| [docs/azure-bot-service.md](docs/azure-bot-service.md) | Azure Bot Service setup, secret rotation, OAuth connection, and app package |
| [docs/vscode-tasks.md](docs/vscode-tasks.md) | VS Code task reference and recommended flows |

## Notes

- The `/chat/stream` endpoint requires `Authorization: Bearer <token>` — see [docs/api-guide.md](docs/api-guide.md).
- Fabric tool calls always require user authentication.
- Local mode uses `DefaultAzureCredential` with interactive fallback.
- M365 mode expects Bot Service user tokens from Teams/Copilot Chat.
- M365 OAuth behavior sends an Adaptive Card sign-in prompt, disables the sign-in action after flow initiation, and supports pasting OAuth magic codes back in chat.
- M365 runtime state access uses helper functions in [`packages/langgraph-fabric-m365/src/langgraph_fabric_m365/oauth.py`](packages/langgraph-fabric-m365/src/langgraph_fabric_m365/oauth.py) instead of direct `TurnState` calls for SDK compatibility.
- Logging supports a base `LOG_LEVEL` plus optional `LOG_LEVEL_OVERRIDE` values such as `langgraph_fabric_core.graph:DEBUG,azure.core:WARNING`.
- DEBUG logs can include large configuration payloads from dependencies. Redact secrets before sharing logs outside your machine.

