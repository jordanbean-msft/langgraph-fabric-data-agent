"""Hosted entrypoint for Teams/Copilot Chat adapter."""

import asyncio
import logging

from langgraph_fabric_data_agent.auth import FabricTokenProvider
from langgraph_fabric_data_agent.config import get_settings
from langgraph_fabric_data_agent.fabric_mcp_client import FabricMcpClient
from langgraph_fabric_data_agent.hosted import create_hosted_app
from langgraph_fabric_data_agent.llm import create_chat_model
from langgraph_fabric_data_agent.logging_setup import configure_logging
from langgraph_fabric_data_agent.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = get_settings()
    token_provider = FabricTokenProvider(settings)
    client = FabricMcpClient(settings, token_provider)
    model = create_chat_model(settings)
    orchestrator = AgentOrchestrator(model, client)
    await create_hosted_app(settings, orchestrator)
    logger.info("Hosted adapter initialized")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
