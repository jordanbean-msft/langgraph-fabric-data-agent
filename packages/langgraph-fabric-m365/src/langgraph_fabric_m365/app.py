"""M365 Agents SDK adapter bridge for Teams and Copilot Chat."""

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
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

from langgraph_fabric_m365.config import M365Settings
from langgraph_fabric_m365.oauth import (
    PENDING_PROMPT_KEY,
    disable_signin_card,
    extract_magic_code,
    get_m365_user_token,
    state_delete,
    state_get,
    state_set,
)
from langgraph_fabric_m365.runtime import (
    build_m365_environment,
    build_m365_sdk_configuration,
)

HISTORY_KEY = "history"


async def create_m365_app(
    settings: M365Settings,
    orchestrator: AgentOrchestrator,
) -> AgentApplication[TurnState]:
    """Create M365 adapter plumbing that can be wired to Teams/Copilot Chat."""
    m365_env = build_m365_environment(settings)
    m365_sdk_configuration = build_m365_sdk_configuration(settings)
    runtime_configuration = {**m365_env, **m365_sdk_configuration}

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
        user_id = getattr(getattr(context.activity, "from_property", None), "id", "m365-user")
        channel_id = getattr(context.activity, "channel_id", None)
        magic_code = extract_magic_code(text)

        if not magic_code and text.strip():
            state_set(state, PENDING_PROMPT_KEY, text)

        fabric_user_token = await get_m365_user_token(
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
            pending_prompt = state_get(state, PENDING_PROMPT_KEY)
            if pending_prompt:
                prompt = pending_prompt
                state_delete(state, PENDING_PROMPT_KEY)
                await context.send_activity("Sign-in complete. Running your previous request.")
            else:
                await context.send_activity("Sign-in complete. Please enter your request.")
                return

        raw_history = state_get(state, HISTORY_KEY) or []
        history: list[BaseMessage] = messages_from_dict(raw_history) if raw_history else []

        streamer = getattr(context, "streaming_response", None)
        if streamer is None:
            raise RuntimeError("M365 channel requires streaming_response for all bot replies")

        chunks: list[str] = []

        # Mark responses as AI-generated in M365 clients that support this metadata.
        streamer.set_generated_by_ai_label(True)

        # Keep the stream open with informative updates while tools execute.
        streamer.queue_informative_update("Working on your request...")

        async for chunk in orchestrator.stream(
            prompt=prompt,
            channel="m365",
            auth_mode="m365",
            user_id=user_id,
            fabric_user_token=fabric_user_token,
            history=history,
        ):
            if chunk.startswith("\n[tool]"):
                status_text = chunk.strip()
                if status_text.startswith("[tool]"):
                    status_text = status_text[len("[tool]") :].strip()
                if status_text:
                    streamer.queue_informative_update(status_text)
            else:
                chunks.append(chunk)
                streamer.queue_text_chunk(chunk)

        await streamer.end_stream()

        response = "".join(chunks)
        history.append(HumanMessage(content=prompt))
        history.append(AIMessage(content=response))
        state_set(state, HISTORY_KEY, messages_to_dict(history))

    @agent_app.activity("invoke")
    async def handle_invoke(context, state: TurnState):
        invoke_name = getattr(context.activity, "name", None)
        if invoke_name in {"signin/tokenExchange", "signin/verifystate", "signin/verifyState"}:
            await disable_signin_card(
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
