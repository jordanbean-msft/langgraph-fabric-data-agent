"""Hosted entrypoint for Teams/Copilot Chat adapter."""

import asyncio
import logging

from langgraph_fabric_data_agent.core.config import get_settings
from langgraph_fabric_data_agent.core.logging import configure_logging
from langgraph_fabric_data_agent.fabric.auth import FabricTokenProvider
from langgraph_fabric_data_agent.fabric.mcp_client import FabricMcpClient
from langgraph_fabric_data_agent.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_data_agent.hosted.app import create_hosted_app
from langgraph_fabric_data_agent.llm.factory import create_chat_model

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
    configure_logging(settings.log_level, settings.log_level_override)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
