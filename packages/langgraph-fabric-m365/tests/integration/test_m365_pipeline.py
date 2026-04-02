"""Integration tests for the M365 package interacting with the core orchestrator.

Tests verify that the M365 app handlers (langgraph-fabric-m365) correctly
drive AgentOrchestrator (langgraph-fabric-core) without requiring real Azure or
Teams services.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, messages_from_dict
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_m365.app import HISTORY_KEY, create_m365_app
from langgraph_fabric_m365.config import M365Settings
from langgraph_fabric_m365.oauth import PENDING_PROMPT_KEY
from microsoft_agents.activity import ActivityTypes


def _make_settings(**overrides) -> M365Settings:
    base = {
        "azure_openai_endpoint": "https://example.services.ai.azure.com/api/projects/demo",
        "azure_openai_deployment_name": "gpt-5.4",
        "azure_openai_api_version": "2025-11-15-preview",
        "azure_openai_scope": "https://ai.azure.com/.default",
        "fabric_data_agent_mcp_url": "https://api.fabric.microsoft.com/v1/mcp/demo",
        "fabric_data_agent_scope": "https://api.fabric.microsoft.com/.default",
        "fabric_data_agent_timeout_seconds": 120,
        "fabric_data_agent_poll_interval_seconds": 2,
        "log_level": "INFO",
        "log_level_override": None,
        "port": 8000,
        "connections_service_connection_id": "service_connection",
        "connections_service_connection_name": "Default Service Connection",
        "connections_service_connection_client_id": "11111111-1111-1111-1111-111111111111",
        "connections_service_connection_tenant_id": "22222222-2222-2222-2222-222222222222",
        "connections_service_connection_auth_type": "ClientSecret",
        "connections_service_connection_client_secret": "secret",
        "microsoft_app_id": "33333333-3333-3333-3333-333333333333",
        "microsoft_app_password": "secret",
        "microsoft_tenant_id": "44444444-4444-4444-4444-444444444444",
        "fabric_oauth_connection_name": "FabricOAuth2",
    }
    base.update(overrides)
    return M365Settings.model_construct(**base)


class _FakeAgentApp:
    """Captures activity handlers without requiring the real M365 SDK."""

    def __init__(self, **kwargs):
        self._handlers: dict[str, object] = {}
        self.adapter = SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient")

    def activity(self, event_type: str):
        def decorator(fn):
            self._handlers[event_type] = fn
            return fn

        return decorator


class _FakeState:
    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def set_value(self, key: str, value: object) -> None:
        self._values[key] = value

    def get_value(self, key: str, _type=None) -> object:
        return self._values.get(key)

    def delete_value(self, key: str) -> None:
        self._values.pop(key, None)


@pytest.fixture
def sdk_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace all M365 SDK classes with lightweight fakes."""
    monkeypatch.setattr("langgraph_fabric_m365.app.MemoryStorage", lambda: SimpleNamespace())
    monkeypatch.setattr(
        "langgraph_fabric_m365.app.MsalConnectionManager", lambda **_: SimpleNamespace()
    )
    monkeypatch.setattr(
        "langgraph_fabric_m365.app.CloudAdapter",
        lambda **_: SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
    )
    monkeypatch.setattr(
        "langgraph_fabric_m365.app.Authorization",
        lambda *args, **_: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "langgraph_fabric_m365.app.ApplicationOptions",
        lambda **_: SimpleNamespace(),
    )
    monkeypatch.setattr("langgraph_fabric_m365.app.AgentApplication", _FakeAgentApp)


def _make_real_orchestrator(response: str = "Orchestrator answer") -> AgentOrchestrator:
    """Build a real AgentOrchestrator backed by a simple fake graph."""

    class FakeGraph:
        async def ainvoke(self, state):
            return {
                **state,
                "messages": state["messages"] + [SimpleNamespace(content=response)],
            }

    orch = AgentOrchestrator.__new__(AgentOrchestrator)
    orch.__dict__["_graph"] = FakeGraph()
    return orch


# ---------------------------------------------------------------------------
# M365 → Core: message handler integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_m365_message_handler_drives_real_orchestrator(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: M365 handler → real AgentOrchestrator → fake graph → activity sent."""
    settings = _make_settings()
    real_orchestrator = _make_real_orchestrator("Revenue is $100M for Q1.")

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, real_orchestrator)
    message_handler = agent_app._handlers["message"]

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="What is revenue?",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    state = _FakeState()

    await message_handler(context, state)

    context.send_activity.assert_awaited_with("Revenue is $100M for Q1.")


@pytest.mark.asyncio
async def test_m365_message_handler_preserves_history_across_turns(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: conversation history is correctly passed and updated across two turns."""
    settings = _make_settings()
    responses = ["First answer", "Second answer"]
    call_count = {"n": 0}

    class _FakeGraph:
        async def ainvoke(self, state):
            response = responses[call_count["n"]]
            call_count["n"] += 1
            return {
                **state,
                "messages": state["messages"] + [SimpleNamespace(content=response)],
            }

    real_orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    real_orchestrator.__dict__["_graph"] = _FakeGraph()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, real_orchestrator)
    message_handler = agent_app._handlers["message"]

    state = _FakeState()

    # First turn
    ctx1 = SimpleNamespace(
        activity=SimpleNamespace(
            text="First question",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    await message_handler(ctx1, state)
    ctx1.send_activity.assert_awaited_with("First answer")

    # Second turn - state now has stored history
    ctx2 = SimpleNamespace(
        activity=SimpleNamespace(
            text="Second question",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    await message_handler(ctx2, state)
    ctx2.send_activity.assert_awaited_with("Second answer")

    # History should now contain 4 messages (2 turns x 2 messages each)
    history_raw = state.get_value(HISTORY_KEY)
    history = messages_from_dict(history_raw)
    assert len(history) == 4
    assert isinstance(history[0], HumanMessage)
    assert history[0].content == "First question"
    assert isinstance(history[1], AIMessage)
    assert history[1].content == "First answer"
    assert isinstance(history[2], HumanMessage)
    assert history[2].content == "Second question"


@pytest.mark.asyncio
async def test_m365_invoke_handler_responds_independently_of_orchestrator(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: invoke events get a 200 without touching the orchestrator."""
    settings = _make_settings()
    real_orchestrator = _make_real_orchestrator()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._disable_signin_card",
        AsyncMock(),
    )

    agent_app = await create_m365_app(settings, real_orchestrator)
    invoke_handler = agent_app._handlers["invoke"]

    context = SimpleNamespace(
        activity=SimpleNamespace(name="signin/verifyState"),
        send_activity=AsyncMock(),
    )

    await invoke_handler(context, _FakeState())

    activity = context.send_activity.await_args.args[0]
    assert activity.type == ActivityTypes.invoke_response
    assert activity.value["status"] == 200


@pytest.mark.asyncio
async def test_m365_sign_in_flow_then_message_uses_pending_prompt(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integration: full sign-in flow - pending prompt is used after token redemption."""
    settings = _make_settings()
    real_orchestrator = _make_real_orchestrator("Answer to pending question")

    # Simulate token redemption success
    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, real_orchestrator)
    message_handler = agent_app._handlers["message"]

    # User sends initial message (no token yet in a real flow, but we're testing
    # the pending-prompt path directly by pre-seeding the state)
    state = _FakeState()
    state.set_value(PENDING_PROMPT_KEY, "What is the quarterly revenue?")

    # User sends magic code
    magic_code_ctx = SimpleNamespace(
        activity=SimpleNamespace(
            text="987654",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )

    await message_handler(magic_code_ctx, state)

    # Orchestrator should have been called with the pending prompt
    calls = magic_code_ctx.send_activity.await_args_list
    responses = [call.args[0] for call in calls]
    assert any("Answer to pending question" == r for r in responses)
    assert state.get_value(PENDING_PROMPT_KEY) is None
