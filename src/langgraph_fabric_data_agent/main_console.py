"""Console entrypoint."""

import asyncio

from langgraph_fabric_data_agent.auth import FabricTokenProvider
from langgraph_fabric_data_agent.config import get_settings
from langgraph_fabric_data_agent.console import run_console
from langgraph_fabric_data_agent.fabric_mcp_client import FabricMcpClient
from langgraph_fabric_data_agent.llm import create_chat_model
from langgraph_fabric_data_agent.logging_setup import configure_logging
from langgraph_fabric_data_agent.orchestrator import AgentOrchestrator


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    token_provider = FabricTokenProvider(settings)
    client = FabricMcpClient(settings, token_provider)
    model = create_chat_model(settings)
    orchestrator = AgentOrchestrator(model, client)
    asyncio.run(run_console(orchestrator))


if __name__ == "__main__":
    main()
