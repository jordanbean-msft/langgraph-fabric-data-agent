"""M365 entrypoint for Teams/Copilot Chat adapter."""

import asyncio
import logging

from aiohttp.web import AppKey, Application, Request, Response, run_app
from langgraph_fabric_core.core.logging import configure_logging
from langgraph_fabric_core.fabric.auth import FabricTokenProvider
from langgraph_fabric_core.fabric.mcp_client import FabricMcpClient
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.llm.factory import create_chat_model
from microsoft_agents.hosting.aiohttp import jwt_authorization_middleware, start_agent_process
from microsoft_agents.hosting.core import AgentApplication, TurnState
from microsoft_agents.hosting.core.authorization import AgentAuthConfiguration

from langgraph_fabric_m365.app import create_m365_app
from langgraph_fabric_m365.config import get_settings

logger = logging.getLogger(__name__)

AGENT_CONFIGURATION_KEY: AppKey[AgentAuthConfiguration] = AppKey("agent_configuration")
AGENT_APP_KEY: AppKey[AgentApplication[TurnState]] = AppKey("agent_app")
ADAPTER_KEY: AppKey[object] = AppKey("adapter")
AGENT_CONFIGURATION_STATE_KEY = "agent_configuration"
AGENT_APP_STATE_KEY = "agent_app"
ADAPTER_STATE_KEY = "adapter"


async def _build_m365_agent_app() -> AgentApplication[TurnState]:
    settings = get_settings()
    token_provider = FabricTokenProvider(settings)
    client = FabricMcpClient(settings, token_provider)
    model = create_chat_model(settings)
    orchestrator = AgentOrchestrator(model, client)
    return await create_m365_app(settings, orchestrator)


def _resolve_agent_auth_configuration(
    agent_app: AgentApplication[TurnState],
    settings,
) -> AgentAuthConfiguration:
    channel_factory = getattr(agent_app.adapter, "_channel_service_client_factory", None)
    connection_manager = getattr(channel_factory, "_connection_manager", None)

    if connection_manager and hasattr(connection_manager, "get_default_connection_configuration"):
        return connection_manager.get_default_connection_configuration()

    return AgentAuthConfiguration(
        client_id=settings.microsoft_app_id,
        tenant_id=settings.microsoft_tenant_id,
        client_secret=settings.microsoft_app_password,
    )


def create_server_app(agent_app: AgentApplication[TurnState], settings) -> Application:
    async def entry_point(request: Request) -> Response:
        response = await start_agent_process(
            request,
            agent_app,
            agent_app.adapter,
        )
        return response or Response(status=201)

    async def health_check(_: Request) -> Response:
        return Response(status=200)

    app = Application(middlewares=[jwt_authorization_middleware])
    app.router.add_post("/api/messages", entry_point)
    app.router.add_get("/api/messages", health_check)
    auth_config = _resolve_agent_auth_configuration(agent_app, settings)
    app[AGENT_CONFIGURATION_KEY] = auth_config
    app[AGENT_APP_KEY] = agent_app
    app[ADAPTER_KEY] = agent_app.adapter

    # Microsoft Agents middleware currently reads app state using string keys.
    app._state[AGENT_CONFIGURATION_STATE_KEY] = auth_config
    app._state[AGENT_APP_STATE_KEY] = agent_app
    app._state[ADAPTER_STATE_KEY] = agent_app.adapter
    return app


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_level_override)

    agent_app = asyncio.run(_build_m365_agent_app())
    server_app = create_server_app(agent_app, settings)

    logger.info(
        "M365 adapter initialized and listening",
        extra={"port": settings.port, "path": "/api/messages"},
    )
    run_app(server_app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
