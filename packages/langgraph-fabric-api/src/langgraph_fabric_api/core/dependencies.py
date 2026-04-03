"""FastAPI dependency injection utilities."""

from functools import lru_cache

from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.llm.factory import create_chat_model
from langgraph_fabric_core.mcp.auth import TokenProvider
from langgraph_fabric_core.mcp.client import McpClient

from langgraph_fabric_api.config import get_settings


@lru_cache(maxsize=1)
def get_orchestrator() -> AgentOrchestrator:
    """Build and cache the default orchestrator instance.

    Returns:
        The AgentOrchestrator singleton.
    """
    settings = get_settings()
    token_provider = TokenProvider(settings)
    mcp_clients = [McpClient(server, token_provider) for server in settings.mcp_servers]
    chat_model = create_chat_model(settings)
    return AgentOrchestrator(chat_model, mcp_clients)
