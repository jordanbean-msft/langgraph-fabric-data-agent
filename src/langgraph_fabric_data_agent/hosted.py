"""M365 Agents SDK hosted bridge for Teams and Copilot Chat."""

from os import environ

from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    ApplicationOptions,
    Authorization,
    MemoryStorage,
    TurnState,
)

from langgraph_fabric_data_agent.config import AppSettings
from langgraph_fabric_data_agent.orchestrator import AgentOrchestrator


async def create_hosted_app(
    settings: AppSettings,
    orchestrator: AgentOrchestrator,
) -> AgentApplication[TurnState]:
    """Create hosted adapter plumbing that can be wired to Teams/Copilot Chat."""
    storage = MemoryStorage()
    connection_manager = MsalConnectionManager(**environ)
    adapter = CloudAdapter(connection_manager=connection_manager)
    authorization = Authorization(storage, connection_manager, **environ)

    app_options = ApplicationOptions(
        adapter=adapter,
        bot_app_id=settings.microsoft_app_id,
        storage=storage,
        long_running_messages=False,
    )
    agent_app: AgentApplication[TurnState] = AgentApplication(
        authorization=authorization,
        options=app_options,
        **environ,
    )

    @agent_app.message(".*")
    async def handle_message(context, _state: TurnState):
        text = getattr(context.activity, "text", "")
        user_id = getattr(getattr(context.activity, "from_property", None), "id", "hosted-user")

        token_result = await context.adapter.get_user_token(
            context,
            settings.fabric_oauth_connection_name,
        )
        if not token_result or not getattr(token_result, "token", None):
            await context.send_activity(
                "Please sign in to continue.",
            )
            return

        response = await orchestrator.run(
            prompt=text,
            channel="hosted",
            auth_mode="hosted",
            user_id=user_id,
            fabric_user_token=token_result.token,
        )
        await context.send_activity(response)

    return agent_app
