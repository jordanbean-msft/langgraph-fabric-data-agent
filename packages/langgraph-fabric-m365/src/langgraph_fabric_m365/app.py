"""M365 Agents SDK adapter bridge for Teams and Copilot Chat."""

import logging
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from microsoft_agents.activity import (
    Activity,
    ActivityTypes,
    ClientCitation,
    ClientCitationAppearance,
    ClientCitationIconName,
    ClientCitationImage,
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.aiohttp.app.streaming import Citation
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
logger = logging.getLogger(__name__)


def _build_citation_marker_text(citation_count: int) -> str:
    """Build inline citation markers expected by Teams/Copilot clients."""
    if citation_count <= 0:
        return ""

    markers = " ".join(f"[doc{index}]" for index in range(1, citation_count + 1))
    return f" {markers}"


def _build_client_citations(
    tool_names: list[str],
    orchestrator: AgentOrchestrator,
) -> list[ClientCitation]:
    """Build rich Teams/Copilot citations for the used MCP tools."""
    citations: list[ClientCitation] = []

    for tool_name in tool_names:
        citation = orchestrator.get_tool_citation(tool_name)
        if citation is None:
            continue

        citations.append(
            ClientCitation(
                position=len(citations) + 1,
                appearance=ClientCitationAppearance(
                    name=citation.title,
                    abstract=citation.content,
                    url=citation.url,
                    image=ClientCitationImage(name=ClientCitationIconName.TEXT.value),
                ),
            )
        )

    return citations


def _set_streamer_citations(streamer: Any, citations: list[ClientCitation]) -> None:
    """Set rich citations on the M365 streaming response.

    The current SDK `set_citations()` helper only preserves title and abstract,
    but Teams/Copilot source cards can also use richer `ClientCitation`
    appearance metadata such as URLs.
    """
    if hasattr(streamer, "_citations"):
        vars(streamer)["_citations"] = citations
        return

    simplified_citations = [
        Citation(
            title=citation.appearance.name if citation.appearance else None,
            content=(citation.appearance.abstract if citation.appearance else "") or "Source",
            url=citation.appearance.url if citation.appearance else None,
        )
        for citation in citations
    ]
    if hasattr(streamer, "set_citations"):
        streamer.set_citations(simplified_citations)


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
        servers_requiring_oauth = [
            server for server in settings.mcp_servers if server.oauth_connection_name
        ]

        if not magic_code and text.strip():
            state_set(state, PENDING_PROMPT_KEY, text)

        mcp_user_tokens: dict[str, str] = {}
        for server in settings.mcp_servers:
            if not server.oauth_connection_name:
                continue
            token = await get_m365_user_token(
                context=context,
                state=state,
                settings=settings,
                connection_name=server.oauth_connection_name,
                user_id=user_id,
                channel_id=channel_id,
                magic_code=magic_code,
            )
            if token:
                mcp_user_tokens[server.name] = token

        if servers_requiring_oauth and not mcp_user_tokens:
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
        used_tool_names: list[str] = []

        def record_tool_event(event: dict[str, object]) -> None:
            event_name = event.get("event")
            if event_name not in {"on_tool_start", "on_tool_end"}:
                return

            tool_name = event.get("name")
            raw_event_data = event.get("data")
            event_data = raw_event_data if isinstance(raw_event_data, dict) else {}
            if not isinstance(tool_name, str):
                return

            if event_name == "on_tool_start":
                if tool_name not in used_tool_names:
                    used_tool_names.append(tool_name)

                logger.debug(
                    "M365 raw tool call input tool=%s input=%s",
                    tool_name,
                    event_data.get("input", event_data),
                )
                return

            logger.debug(
                "M365 raw tool call output tool=%s output=%s",
                tool_name,
                event_data.get("output", event_data),
            )

        # Mark responses as AI-generated in M365 clients that support this metadata.
        streamer.set_generated_by_ai_label(True)

        # Keep the stream open with informative updates while tools execute.
        streamer.queue_informative_update("Working on your request...")

        async for chunk in orchestrator.stream(
            prompt=prompt,
            channel="m365",
            auth_mode="m365",
            user_id=user_id,
            mcp_user_tokens=mcp_user_tokens,
            history=history,
            event_callback=record_tool_event,
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

        citations = _build_client_citations(used_tool_names, orchestrator)
        if citations:
            citation_marker_text = _build_citation_marker_text(len(citations))
            chunks.append(citation_marker_text)
            streamer.queue_text_chunk(citation_marker_text)
            logger.debug(
                "Setting M365 citations for tools=%s titles=%s",
                used_tool_names,
                [citation.appearance.name for citation in citations if citation.appearance],
            )
            _set_streamer_citations(streamer, citations)

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

        invoke_response_payload = {
            "type": ActivityTypes.invoke_response,
            "value": {"status": 200, "body": {}},
        }
        for key, value in {
            "from": getattr(context.activity, "recipient", None),
            "recipient": getattr(context.activity, "from_property", None),
            "conversation": getattr(context.activity, "conversation", None),
        }.items():
            if value is not None:
                invoke_response_payload[key] = value

        await context.send_activity(Activity.model_validate(invoke_response_payload))

    return agent_app
