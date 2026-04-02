# langgraph-fabric-core

Interface-agnostic core package for the LangGraph Fabric Data Agent sample.
This package has **no** dependency on FastAPI, aiohttp, or the M365 Agents SDK.

## Modules

| Module | Purpose |
| --- | --- |
| `core/config.py` | Shared base settings (`CoreSettings`) via pydantic-settings |
| `core/logging.py` | Structured logs with correlation context |
| `fabric/auth.py` | Local and M365 token strategies for Fabric |
| `fabric/mcp_client.py` | Strict JSON-RPC MCP client wrapper for Fabric Data Agent endpoints |
| `fabric/tools.py` | LangChain tool wrappers over MCP |
| `graph/workflow.py` | LangGraph state graph definition and tool routing |
| `graph/orchestrator.py` | Shared run and stream orchestration |
| `llm/factory.py` | Azure OpenAI / Foundry chat model factory |

## Usage

This package is consumed by the interface packages (`langgraph-fabric-api`, `langgraph-fabric-console`, `langgraph-fabric-m365`).
It is not intended to be run directly.

See the [architecture guide](../../docs/architecture.md) for full details.

