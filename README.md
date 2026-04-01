---
title: LangGraph Fabric Data Agent Sample
description: Minimal Python sample showing a LangGraph agent calling a Fabric Data Agent through MCP with local and hosted surfaces
---

## Overview

This repository demonstrates a LangGraph-based AI agent that calls a Fabric Data Agent via MCP.

The sample includes two interaction surfaces:

- Terminal console with streaming responses.
- FastAPI streaming endpoint that can be reused by hosted adapters.

The hosted path is wired for Teams and Copilot Chat style usage through the M365 Agents SDK patterns.

## Architecture

- [src/langgraph_fabric_data_agent/core/config.py](src/langgraph_fabric_data_agent/core/config.py): centralized environment settings via pydantic-settings.
- [src/langgraph_fabric_data_agent/core/logging.py](src/langgraph_fabric_data_agent/core/logging.py): structured logs with correlation context.
- [src/langgraph_fabric_data_agent/fabric/auth.py](src/langgraph_fabric_data_agent/fabric/auth.py): local and hosted token strategies for Fabric.
- [src/langgraph_fabric_data_agent/fabric/mcp_client.py](src/langgraph_fabric_data_agent/fabric/mcp_client.py): strict JSON-RPC MCP client wrapper.
- [src/langgraph_fabric_data_agent/fabric/tools.py](src/langgraph_fabric_data_agent/fabric/tools.py): LangGraph tool integration over MCP.
- [src/langgraph_fabric_data_agent/graph/workflow.py](src/langgraph_fabric_data_agent/graph/workflow.py): graph definition and tool routing.
- [src/langgraph_fabric_data_agent/graph/orchestrator.py](src/langgraph_fabric_data_agent/graph/orchestrator.py): shared run and stream orchestration.
- [src/langgraph_fabric_data_agent/api/app.py](src/langgraph_fabric_data_agent/api/app.py): FastAPI surface.
- [src/langgraph_fabric_data_agent/cli/console.py](src/langgraph_fabric_data_agent/cli/console.py): terminal surface.
- [src/langgraph_fabric_data_agent/hosted/app.py](src/langgraph_fabric_data_agent/hosted/app.py): hosted M365 adapter bridge and route wiring.
- [src/langgraph_fabric_data_agent/hosted/oauth.py](src/langgraph_fabric_data_agent/hosted/oauth.py): hosted OAuth card flow, magic code handling, and hosted token resolution.
- [src/langgraph_fabric_data_agent/hosted/runtime.py](src/langgraph_fabric_data_agent/hosted/runtime.py): hosted runtime environment and SDK configuration builders.

## Prerequisites

- Python 3.12
- uv
- Access to:
- Azure OpenAI / Foundry deployment (GPT-5.4)
- Fabric Data Agent MCP endpoint
- Bot Service credentials for hosted mode

## Setup

1. Copy [.env.example](.env.example) to `.env` and fill your values.
2. Install dependencies:

```bash
uv sync --extra dev
```

## Run

API surface:

```bash
uv run python -m langgraph_fabric_data_agent.main_api
```

Console surface:

```bash
uv run python -m langgraph_fabric_data_agent.main_console
```

Hosted adapter initialization:

```bash
uv run python -m langgraph_fabric_data_agent.main_hosted
```

## Validate

```bash
uv run ruff check .
uv run pytest tests/unit
uv run pytest tests/integration
```

## Notes

- FastAPI endpoints are intentionally unauthenticated for this demo.
- Fabric tool calls always require user authentication.
- Local mode uses DefaultAzureCredential with interactive fallback.
- Hosted mode expects Bot Service user tokens.
- Hosted OAuth behavior sends an Adaptive Card sign-in prompt, disables the sign-in action after flow initiation, and supports pasting OAuth magic codes back in chat.
- Hosted runtime state access uses helper functions in [src/langgraph_fabric_data_agent/hosted/oauth.py](src/langgraph_fabric_data_agent/hosted/oauth.py) instead of direct TurnState get_value and set_value calls for SDK compatibility.
- Logging supports a base `LOG_LEVEL` plus optional `LOG_LEVEL_OVERRIDE` values such as `langgraph_fabric_data_agent.graph:DEBUG,azure.core:WARNING`.
- DEBUG logs can include large configuration payloads from dependencies. Redact secrets before sharing logs outside your machine.
