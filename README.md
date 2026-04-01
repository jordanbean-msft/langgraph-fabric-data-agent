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
- [src/langgraph_fabric_data_agent/hosted/app.py](src/langgraph_fabric_data_agent/hosted/app.py): hosted M365 adapter bridge.

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
- Logging supports a base `LOG_LEVEL` plus optional `LOG_LEVEL_OVERRIDE` values such as `langgraph_fabric_data_agent.graph:DEBUG,azure.core:WARNING`.
