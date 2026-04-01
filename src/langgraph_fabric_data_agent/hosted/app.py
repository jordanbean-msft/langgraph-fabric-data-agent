"""M365 Agents SDK hosted bridge for Teams and Copilot Chat."""

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)
from microsoft_agents.activity import Activity, ActivityTypes
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    ApplicationOptions,
    Authorization,
    MemoryStorage,
    TurnState,
)

from langgraph_fabric_data_agent.core.config import AppSettings
from langgraph_fabric_data_agent.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_data_agent.hosted.oauth import (
    PENDING_PROMPT_KEY,
    _disable_signin_card,
    _extract_magic_code,
    _get_hosted_user_token,
    _state_delete,
    _state_get,
    _state_set,
)
from langgraph_fabric_data_agent.hosted.runtime import (
    _build_hosted_environment,
    _build_hosted_sdk_configuration,
)

HISTORY_KEY = "history"


async def create_hosted_app(
    settings: AppSettings,
    orchestrator: AgentOrchestrator,
) -> AgentApplication[TurnState]:
    """Create hosted adapter plumbing that can be wired to Teams/Copilot Chat."""
    hosted_env = _build_hosted_environment(settings)
    hosted_sdk_configuration = _build_hosted_sdk_configuration(settings)
    runtime_configuration = {**hosted_env, **hosted_sdk_configuration}

    storage = MemoryStorage()
    connection_manager = MsalConnectionManager(**runtime_configuration)
    adapter = CloudAdapter(connection_manager=connection_manager)
    authorization = Authorization(storage, connection_manager, **runtime_configuration)

    app_options = ApplicationOptions(
        adapter=adapter,
        bot_app_id=settings.microsoft_app_id,
        storage=storage,
        long_running_messages=False,
    )
    agent_app: AgentApplication[TurnState] = AgentApplication(
        authorization=authorization,
        options=app_options,
        **runtime_configuration,
    )

    @agent_app.activity("message")
    async def handle_message(context, state: TurnState):
        text = getattr(context.activity, "text", "")
        user_id = getattr(getattr(context.activity, "from_property", None), "id", "hosted-user")
        channel_id = getattr(context.activity, "channel_id", None)
        magic_code = _extract_magic_code(text)

        if not magic_code and text.strip():
            _state_set(state, PENDING_PROMPT_KEY, text)

        fabric_user_token = await _get_hosted_user_token(
            context=context,
            state=state,
            settings=settings,
            user_id=user_id,
            channel_id=channel_id,
            magic_code=magic_code,
        )

        if not fabric_user_token:
            if magic_code:
                await context.send_activity(
                    "We could not redeem that verification code. Please open the sign-in card and try again.",
                )
            return

        prompt = text
        if magic_code:
            pending_prompt = _state_get(state, PENDING_PROMPT_KEY)
            if pending_prompt:
                prompt = pending_prompt
                _state_delete(state, PENDING_PROMPT_KEY)
                await context.send_activity("Sign-in complete. Running your previous request.")
            else:
                await context.send_activity("Sign-in complete. Please enter your request.")
                return

        raw_history = _state_get(state, HISTORY_KEY) or []
        history: list[BaseMessage] = messages_from_dict(raw_history) if raw_history else []

        response = await orchestrator.run(
            prompt=prompt,
            channel="hosted",
            auth_mode="hosted",
            user_id=user_id,
            fabric_user_token=fabric_user_token,
            history=history,
        )

        history.append(HumanMessage(content=prompt))
        history.append(AIMessage(content=response))
        _state_set(state, HISTORY_KEY, messages_to_dict(history))

        await context.send_activity(response)

    @agent_app.activity("invoke")
    async def handle_invoke(context, state: TurnState):
        invoke_name = getattr(context.activity, "name", None)
        if invoke_name in {"signin/tokenExchange", "signin/verifystate", "signin/verifyState"}:
            await _disable_signin_card(
                context,
                state,
                "Sign-in is in progress. Complete the sign-in flow and return to this chat.",
            )

        await context.send_activity(
            Activity(
                type=ActivityTypes.invoke_response,
                value={"status": 200, "body": {}},
            )
        )

    return agent_app
