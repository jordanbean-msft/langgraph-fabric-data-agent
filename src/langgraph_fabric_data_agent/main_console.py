"""Console entrypoint."""

import asyncio

from langgraph_fabric_data_agent.cli.console import run_console
from langgraph_fabric_data_agent.core.config import get_settings
from langgraph_fabric_data_agent.core.logging import configure_logging
from langgraph_fabric_data_agent.fabric.auth import FabricTokenProvider
from langgraph_fabric_data_agent.fabric.mcp_client import FabricMcpClient
from langgraph_fabric_data_agent.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_data_agent.llm.factory import create_chat_model


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_level_override)
    token_provider = FabricTokenProvider(settings)
    client = FabricMcpClient(settings, token_provider)
    model = create_chat_model(settings)
    orchestrator = AgentOrchestrator(model, client)
    asyncio.run(run_console(orchestrator))


if __name__ == "__main__":
    main()
