"""Unit tests for the M365 app handlers (app.py)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
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


@pytest.mark.asyncio
async def test_message_handler_calls_orchestrator_and_sends_response(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value="Here is the answer")

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="What is the answer?",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    state = _FakeState()

    await message_handler(context, state)

    orchestrator.run.assert_awaited_once()
    call_kwargs = orchestrator.run.await_args.kwargs
    assert call_kwargs["prompt"] == "What is the answer?"
    assert call_kwargs["auth_mode"] == "m365"
    assert call_kwargs["user_id"] == "user-1"
    assert call_kwargs["fabric_user_token"] == "fabric-token"
    context.send_activity.assert_awaited_with("Here is the answer")


@pytest.mark.asyncio
async def test_message_handler_does_not_call_orchestrator_when_no_token(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value=None),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="Hello",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    await message_handler(context, _FakeState())

    orchestrator.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_message_handler_stores_conversation_history(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value="Answer text")

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="Tell me about sales",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )
    state = _FakeState()

    await message_handler(context, state)

    history_raw = state.get_value(HISTORY_KEY)
    assert history_raw is not None
    assert len(history_raw) == 2  # user message + AI response
    assert history_raw[0]["data"]["content"] == "Tell me about sales"
    assert history_raw[1]["data"]["content"] == "Answer text"


@pytest.mark.asyncio
async def test_message_handler_uses_pending_prompt_after_magic_code(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value="Response to pending")

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    state = _FakeState()
    state.set_value(PENDING_PROMPT_KEY, "What are top 5 customers?")

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="123456",  # magic code
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )

    await message_handler(context, state)

    call_kwargs = orchestrator.run.await_args.kwargs
    assert call_kwargs["prompt"] == "What are top 5 customers?"
    assert state.get_value(PENDING_PROMPT_KEY) is None


@pytest.mark.asyncio
async def test_message_handler_sends_completion_after_sign_in_with_pending_prompt(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After magic code with pending prompt, a confirmation activity is sent."""
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock(return_value="Response")

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value="fabric-token"),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    state = _FakeState()
    state.set_value(PENDING_PROMPT_KEY, "pending question")

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="654321",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )

    await message_handler(context, state)

    send_calls = context.send_activity.await_args_list
    # First call is confirmation, second is the response
    assert any("sign-in complete" in str(call).lower() for call in send_calls)


@pytest.mark.asyncio
async def test_message_handler_notifies_user_when_magic_code_fails(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value=None),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="123456",  # magic code, but token fails
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )

    await message_handler(context, _FakeState())

    orchestrator.run.assert_not_awaited()
    context.send_activity.assert_awaited_once()
    error_msg = context.send_activity.await_args.args[0]
    assert "verification code" in error_msg.lower()


@pytest.mark.asyncio
async def test_message_handler_sends_sign_in_prompt_when_no_token_and_no_magic_code(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When there is no token and user sends normal text, the prompt is stored for later."""
    settings = _make_settings()
    orchestrator = MagicMock()
    orchestrator.run = AsyncMock()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._get_m365_user_token",
        AsyncMock(return_value=None),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    message_handler = agent_app._handlers["message"]

    state = _FakeState()
    context = SimpleNamespace(
        activity=SimpleNamespace(
            text="Show me the top customers",
            from_property=SimpleNamespace(id="user-1"),
            channel_id="msteams",
        ),
        send_activity=AsyncMock(),
    )

    await message_handler(context, state)

    orchestrator.run.assert_not_awaited()
    assert state.get_value(PENDING_PROMPT_KEY) == "Show me the top customers"


@pytest.mark.asyncio
async def test_invoke_handler_sends_200_response_for_token_exchange(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._disable_signin_card",
        AsyncMock(),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    invoke_handler = agent_app._handlers["invoke"]

    context = SimpleNamespace(
        activity=SimpleNamespace(name="signin/tokenExchange"),
        send_activity=AsyncMock(),
    )

    await invoke_handler(context, _FakeState())

    context.send_activity.assert_awaited_once()
    activity_sent = context.send_activity.await_args.args[0]
    assert activity_sent.type == ActivityTypes.invoke_response
    assert activity_sent.value["status"] == 200


@pytest.mark.asyncio
async def test_invoke_handler_sends_200_response_for_verify_state(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _make_settings()
    orchestrator = MagicMock()

    monkeypatch.setattr(
        "langgraph_fabric_m365.app._disable_signin_card",
        AsyncMock(),
    )

    agent_app = await create_m365_app(settings, orchestrator)
    invoke_handler = agent_app._handlers["invoke"]

    context = SimpleNamespace(
        activity=SimpleNamespace(name="signin/verifyState"),
        send_activity=AsyncMock(),
    )

    await invoke_handler(context, _FakeState())

    activity_sent = context.send_activity.await_args.args[0]
    assert activity_sent.type == ActivityTypes.invoke_response
    assert activity_sent.value["status"] == 200


@pytest.mark.asyncio
async def test_invoke_handler_sends_200_response_for_unknown_invoke(
    sdk_mocks: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-OAuth invoke events still receive a 200 response."""
    settings = _make_settings()
    orchestrator = MagicMock()

    agent_app = await create_m365_app(settings, orchestrator)
    invoke_handler = agent_app._handlers["invoke"]

    context = SimpleNamespace(
        activity=SimpleNamespace(name="some/otherInvoke"),
        send_activity=AsyncMock(),
    )

    await invoke_handler(context, _FakeState())

    activity_sent = context.send_activity.await_args.args[0]
    assert activity_sent.value["status"] == 200
