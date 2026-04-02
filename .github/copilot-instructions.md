---
title: Repository Copilot Instructions
description: Repository-wide guidance for implementing and validating this Python LangGraph monorepo sample
---

## Purpose

This repository is a Python monorepo sample demonstrating a LangGraph-based AI agent calling a Fabric Data Agent via MCP. It is structured as a uv workspace with four packages that cleanly separate the core LangGraph implementation from each client interface. Keep implementation simple, explicit, and testable.

## Monorepo package layout

```
packages/
  langgraph-fabric-core/     # Interface-agnostic: graph, orchestrator, Fabric MCP client, auth, LLM factory
  langgraph-fabric-api/      # FastAPI streaming interface (depends on core)
  langgraph-fabric-console/  # Interactive terminal interface (depends on core)
  langgraph-fabric-m365/     # M365 Agents SDK / Teams / Copilot Chat (depends on core)
```

The core package has **no** dependency on FastAPI, aiohttp, or the M365 Agents SDK.

## Required engineering standards

- Always use uv for environment and dependency management.
- Keep Python imports at the top of files.
- Do not use lazy imports or wrap imports in try/except blocks.
- Prefer pydantic-settings for centralized configuration; each client package has its own settings class.
- Use structured logging with correlation identifiers.
- Keep FastAPI endpoints unauthenticated in this sample.
- Require user authentication for Fabric calls.
- Use streaming responses for console and API interaction.

## Build and validation commands

- Sync all packages: `uv sync --all-packages --extra dev`
- Run lint: `uv run ruff check .`
- Run all tests: `uv run pytest`
- Run API: `uv run langgraph-fabric-api`
- Run console: `uv run langgraph-fabric-console`
- Run M365 adapter: `uv run langgraph-fabric-m365`

## Architecture map

### langgraph-fabric-core (`packages/langgraph-fabric-core/src/langgraph_fabric_core/`)
- `core/config.py`: shared base settings (`CoreSettings`) — Azure OpenAI, Fabric MCP, logging, port
- `core/logging.py`: logging setup and correlation helpers
- `fabric/auth.py`: local and M365 token strategies for Fabric
- `fabric/mcp_client.py`: strict MCP protocol wrapper for Fabric
- `fabric/tools.py`: LangChain tool wrappers over Fabric MCP
- `graph/workflow.py`: LangGraph state graph and routing
- `graph/orchestrator.py`: shared run and stream orchestration
- `llm/factory.py`: Azure OpenAI / Foundry chat model factory

### langgraph-fabric-api (`packages/langgraph-fabric-api/src/langgraph_fabric_api/`)
- `config.py`: `ApiSettings(CoreSettings)` reading from `packages/langgraph-fabric-api/.env` — adds OBO fields
- `app.py`: FastAPI endpoints
- `main.py`: API entrypoint

### langgraph-fabric-console (`packages/langgraph-fabric-console/src/langgraph_fabric_console/`)
- `config.py`: `ConsoleSettings(CoreSettings)` reading from `packages/langgraph-fabric-console/.env`
- `console.py`: terminal experience with streaming
- `main.py`: console entrypoint

### langgraph-fabric-m365 (`packages/langgraph-fabric-m365/src/langgraph_fabric_m365/`)
- `config.py`: `M365Settings(CoreSettings)` reading from `packages/langgraph-fabric-m365/.env` — adds M365 bot fields
- `app.py`: M365 Agents SDK adapter bridge and route handlers
- `oauth.py`: M365 OAuth adaptive card flow, magic code handling, and M365 token resolution
- `runtime.py`: M365 runtime env and SDK configuration
- `main.py`: M365 adapter entrypoint

## M365 implementation guardrails

- Keep M365 OAuth behavior user-friendly: send adaptive sign-in cards, disable sign-in action after initiation, and allow magic code redemption from chat messages.
- When writing M365 state code, use the shared state helpers in `langgraph_fabric_m365/oauth.py` instead of calling TurnState.get_value directly to avoid SDK compatibility issues.
- Keep M365 files modular: routing in `app.py`, OAuth behavior in `oauth.py`, runtime configuration in `runtime.py`.

## Configuration rules

- `CoreSettings` lives in `langgraph-fabric-core` and contains only shared settings (Azure OpenAI, Fabric MCP, logging, port, and optional microsoft_app_id/tenant_id for device-code auth).
- Each client package (`api`, `console`, `m365`) defines its own settings class that extends `CoreSettings` and reads from a `.env` file in its own package directory.
- Use the package-local `get_settings()` in each client package, not the core one.

## Dependency rules

- `langgraph-fabric-core` must not import from `langgraph_fabric_api`, `langgraph_fabric_console`, or `langgraph_fabric_m365`.
- Interface packages (`api`, `console`, `m365`) declare `langgraph-fabric-core` as a workspace dependency.
- Tests in each package only import from that package and `langgraph-fabric-core`.

## Pull request quality bar

- Keep the demo straightforward and easy to read.
- Include tests for all newly added behavior.
- Prefer deterministic mocks over network calls in tests.
- Keep commit scope coherent and focused.
