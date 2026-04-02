"""Console entrypoint."""

import asyncio

from langgraph_fabric_core.core.logging import configure_logging
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.llm.factory import create_chat_model
from langgraph_fabric_core.mcp.auth import TokenProvider
from langgraph_fabric_core.mcp.client import McpClient

from langgraph_fabric_console.config import get_settings
from langgraph_fabric_console.console import run_console


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_level_override)
    token_provider = TokenProvider(settings)
    clients = [McpClient(server, token_provider) for server in settings.mcp_servers]
    model = create_chat_model(settings)
    orchestrator = AgentOrchestrator(model, clients)
    asyncio.run(run_console(orchestrator, settings, token_provider))


if __name__ == "__main__":
    main()
