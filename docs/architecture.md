---
title: Architecture
description: Per-package architecture details for the LangGraph Fabric Data Agent sample
ms.date: 2026-04-01
---

# Architecture

This sample is organized as a **uv workspace** with four independent Python packages.
`langgraph-fabric-core` has **no** dependency on FastAPI, aiohttp, or the M365 Agents SDK.
Each interface package depends only on core.

```
packages/
  langgraph-fabric-core/     # Interface-agnostic: graph, orchestrator, MCP clients, auth, LLM factory
  langgraph-fabric-api/      # FastAPI streaming interface (depends on core)
  langgraph-fabric-console/  # Interactive terminal interface (depends on core)
  langgraph-fabric-m365/     # M365 Agents SDK / Teams / Copilot Chat (depends on core)
```

## langgraph-fabric-core

Source: [`packages/langgraph-fabric-core/`](../packages/langgraph-fabric-core/)

The interface-agnostic package that all client packages depend on.

| Module | Purpose |
| --- | --- |
| [`core/config.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/core/config.py) | Shared base settings via pydantic-settings (`CoreSettings`) |
| [`core/logging.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/core/logging.py) | Structured logs with correlation context |
| [`mcp/auth.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/mcp/auth.py) | Local and M365 token strategies for MCP scopes |
| [`mcp/client.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/mcp/client.py) | Strict JSON-RPC MCP client wrapper |
| [`mcp/tools.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/mcp/tools.py) | LangChain tool wrappers over MCP |
| [`graph/workflow.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/graph/workflow.py) | LangGraph state graph definition and tool routing |
| [`graph/orchestrator.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/graph/orchestrator.py) | Shared run and stream orchestration |
| [`llm/factory.py`](../packages/langgraph-fabric-core/src/langgraph_fabric_core/llm/factory.py) | Azure OpenAI / Foundry chat model factory |

## langgraph-fabric-api

Source: [`packages/langgraph-fabric-api/`](../packages/langgraph-fabric-api/)

FastAPI streaming endpoint for HTTP clients.

| Module | Purpose |
| --- | --- |
| [`config.py`](../packages/langgraph-fabric-api/src/langgraph_fabric_api/config.py) | API-specific settings (`ApiSettings`) reading from `.env` |
| [`app.py`](../packages/langgraph-fabric-api/src/langgraph_fabric_api/app.py) | FastAPI surface with `/health` and `/chat/stream` |
| [`main.py`](../packages/langgraph-fabric-api/src/langgraph_fabric_api/main.py) | API entrypoint (`langgraph-fabric-api` script) |

## langgraph-fabric-console

Source: [`packages/langgraph-fabric-console/`](../packages/langgraph-fabric-console/)

Interactive terminal surface with streaming responses.

| Module | Purpose |
| --- | --- |
| [`config.py`](../packages/langgraph-fabric-console/src/langgraph_fabric_console/config.py) | Console-specific settings (`ConsoleSettings`) reading from `.env` |
| [`console.py`](../packages/langgraph-fabric-console/src/langgraph_fabric_console/console.py) | Interactive terminal surface with streaming |
| [`main.py`](../packages/langgraph-fabric-console/src/langgraph_fabric_console/main.py) | Console entrypoint (`langgraph-fabric-console` script) |

## langgraph-fabric-m365

Source: [`packages/langgraph-fabric-m365/`](../packages/langgraph-fabric-m365/)

M365 adapter for Teams and Copilot Chat via the M365 Agents SDK.

| Module | Purpose |
| --- | --- |
| [`config.py`](../packages/langgraph-fabric-m365/src/langgraph_fabric_m365/config.py) | M365-specific settings (`M365Settings`) reading from `.env` |
| [`app.py`](../packages/langgraph-fabric-m365/src/langgraph_fabric_m365/app.py) | M365 adapter bridge and route wiring |
| [`oauth.py`](../packages/langgraph-fabric-m365/src/langgraph_fabric_m365/oauth.py) | M365 OAuth card flow, magic code handling, and M365 token resolution |
| [`runtime.py`](../packages/langgraph-fabric-m365/src/langgraph_fabric_m365/runtime.py) | M365 runtime environment and SDK configuration builders |
| [`main.py`](../packages/langgraph-fabric-m365/src/langgraph_fabric_m365/main.py) | M365 adapter entrypoint (`langgraph-fabric-m365` script) |

## Dependency rules

- `langgraph-fabric-core` must not import from `langgraph_fabric_api`, `langgraph_fabric_console`, or `langgraph_fabric_m365`.
- Interface packages (`api`, `console`, `m365`) declare `langgraph-fabric-core` as a workspace dependency.
- Tests in each package only import from that package and `langgraph-fabric-core`.
