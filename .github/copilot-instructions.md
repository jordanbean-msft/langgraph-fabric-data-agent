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
- Prefer pydantic-settings for centralized configuration.
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
- Run hosted adapter: `uv run langgraph-fabric-m365`

## Architecture map

### langgraph-fabric-core (`packages/langgraph-fabric-core/src/langgraph_fabric_core/`)
- `core/config.py`: environment and settings models
- `core/logging.py`: logging setup and correlation helpers
- `fabric/auth.py`: local and hosted token strategies
- `fabric/mcp_client.py`: strict MCP protocol wrapper for Fabric
- `fabric/tools.py`: LangChain tool wrappers over Fabric MCP
- `graph/workflow.py`: LangGraph state graph and routing
- `graph/orchestrator.py`: shared run and stream orchestration
- `llm/factory.py`: Azure OpenAI / Foundry chat model factory

### langgraph-fabric-api (`packages/langgraph-fabric-api/src/langgraph_fabric_api/`)
- `app.py`: FastAPI endpoints
- `main.py`: API entrypoint

### langgraph-fabric-console (`packages/langgraph-fabric-console/src/langgraph_fabric_console/`)
- `console.py`: terminal experience with streaming
- `main.py`: console entrypoint

### langgraph-fabric-m365 (`packages/langgraph-fabric-m365/src/langgraph_fabric_m365/`)
- `app.py`: M365 Agents SDK hosted bridge and route handlers
- `oauth.py`: hosted OAuth adaptive card flow, magic code handling, and state shims
- `runtime.py`: hosted runtime env and SDK configuration
- `main.py`: M365 hosted adapter entrypoint

## Hosted implementation guardrails

- Keep hosted OAuth behavior user-friendly: send adaptive sign-in cards, disable sign-in action after initiation, and allow magic code redemption from chat messages.
- When writing hosted state code, use the shared state helpers in `langgraph_fabric_m365/oauth.py` instead of calling TurnState.get_value directly to avoid SDK compatibility issues.
- Keep hosted files modular: routing in `app.py`, OAuth behavior in `oauth.py`, runtime configuration in `runtime.py`.

## Dependency rules

- `langgraph-fabric-core` must not import from `langgraph_fabric_api`, `langgraph_fabric_console`, or `langgraph_fabric_m365`.
- Interface packages (`api`, `console`, `m365`) declare `langgraph-fabric-core` as a workspace dependency.
- Tests in each package only import from that package and `langgraph-fabric-core`.

## Pull request quality bar

- Keep the demo straightforward and easy to read.
- Include tests for all newly added behavior.
- Prefer deterministic mocks over network calls in tests.
- Keep commit scope coherent and focused.
