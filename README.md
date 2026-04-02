---
title: LangGraph Fabric Data Agent Sample
description: Python monorepo sample showing a LangGraph agent calling a Fabric Data Agent through MCP, structured as independent packages for core logic and each client interface
ms.date: 2026-04-01
---

[![CI](https://github.com/jordanbean-msft/langgraph-fabric-data-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/jordanbean-msft/langgraph-fabric-data-agent/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/jordanbean-msft/langgraph-fabric-data-agent)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)

## Overview

This repository demonstrates a LangGraph-based AI agent that can call MCP servers or run in chat-only mode.

The sample is organized as a **uv workspace** with four independent Python packages:

| Package | Description |
| --- | --- |
| [`langgraph-fabric-core`](packages/langgraph-fabric-core/) | Interface-agnostic: graph, orchestrator, MCP client integration, auth, LLM factory |
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
- Optional access to one or more MCP server endpoints
- A signed-in user account that can authenticate to Azure and any configured MCP backend when tool calls are enabled

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
cp packages/langgraph-fabric-console/.env.example packages/langgraph-fabric-console/.env

# FastAPI server
cp packages/langgraph-fabric-api/.env.example packages/langgraph-fabric-api/.env

# M365 adapter (Teams / Copilot Chat)
cp packages/langgraph-fabric-m365/.env.example packages/langgraph-fabric-m365/.env
```

3. Fill the Azure OpenAI values in the copied file.
4. Set `MCP_SERVERS` only if you want MCP-backed tools. Leave it unset or set it to `[]` for chat-only mode.
5. For the M365 adapter, also set `MICROSOFT_APP_ID`, `MICROSOFT_APP_PASSWORD`, `MICROSOFT_TENANT_ID`, and the `CONNECTIONS__SERVICE_CONNECTION__*` values from the [app registration reference](docs/app-registration.md). In `MCP_SERVERS`, set `oauth_connection_name` for each server that needs Bot Service OAuth.

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

- API and M365 channels still require authenticated users even in chat-only mode.
- With `MCP_SERVERS=[]`, the sample runs in chat-only mode without MCP tool calls.
- The `/chat/stream` endpoint always requires `Authorization: Bearer <token>`. See [docs/api-guide.md](docs/api-guide.md).
- Local mode uses `DefaultAzureCredential` with interactive fallback when MCP-backed calls are enabled.
- M365 chat-only access is protected by the Teams/Copilot JWT validated at `/api/messages`. Bot Service OAuth is only needed for MCP servers that declare `oauth_connection_name`.
- M365 OAuth behavior sends an Adaptive Card sign-in prompt, disables the sign-in action after flow initiation, and supports pasting OAuth magic codes back in chat.
- Logging supports a base `LOG_LEVEL` plus optional `LOG_LEVEL_OVERRIDE` values such as `langgraph_fabric_core.graph:DEBUG,azure.core:WARNING`.
