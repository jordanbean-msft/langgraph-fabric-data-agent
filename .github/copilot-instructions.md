---
title: Repository Copilot Instructions
description: Repository-wide guidance for implementing and validating this Python LangGraph sample
---

## Purpose

This repository is a Python sample that demonstrates a LangGraph-based AI agent calling a Fabric Data Agent via MCP. Keep implementation simple, explicit, and testable.

## Required engineering standards

* Always use uv for environment and dependency management.
* Keep Python imports at the top of files.
* Do not use lazy imports or wrap imports in try/except blocks.
* Prefer pydantic-settings for centralized configuration.
* Use structured logging with correlation identifiers.
* Keep FastAPI endpoints unauthenticated in this sample.
* Require user authentication for Fabric calls.
* Use streaming responses for console and API interaction.

## Build and validation commands

* Sync dependencies: uv sync --extra dev
* Run lint: uv run ruff check .
* Run unit tests: uv run pytest tests/unit
* Run integration tests: uv run pytest tests/integration
* Run all tests: uv run pytest
* Run API: uv run python -m langgraph_fabric_data_agent.main_api
* Run console: uv run python -m langgraph_fabric_data_agent.main_console
* Run hosted adapter: uv run python -m langgraph_fabric_data_agent.main_hosted

## Architecture map

* src/langgraph_fabric_data_agent/core/config.py: environment and settings models
* src/langgraph_fabric_data_agent/core/logging.py: logging setup and correlation helpers
* src/langgraph_fabric_data_agent/fabric/auth.py: local and hosted token strategies
* src/langgraph_fabric_data_agent/fabric/mcp_client.py: strict MCP protocol wrapper for Fabric
* src/langgraph_fabric_data_agent/fabric/tools.py: LangChain tool wrappers over Fabric MCP
* src/langgraph_fabric_data_agent/graph/workflow.py: LangGraph state graph and routing
* src/langgraph_fabric_data_agent/graph/orchestrator.py: shared run and stream orchestration
* src/langgraph_fabric_data_agent/api/app.py: FastAPI endpoints
* src/langgraph_fabric_data_agent/cli/console.py: terminal experience with streaming
* src/langgraph_fabric_data_agent/hosted/app.py: M365 Agents SDK hosted bridge

## Pull request quality bar

* Keep the demo straightforward and easy to read.
* Include tests for all newly added behavior.
* Prefer deterministic mocks over network calls in tests.
* Keep commit scope coherent and focused.
