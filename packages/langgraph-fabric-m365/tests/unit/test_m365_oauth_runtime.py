from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp.client_exceptions import ClientResponseError
from langgraph_fabric_m365.config import M365Settings
from langgraph_fabric_m365.oauth import (
    OAUTH_CARD_ACTIVITY_ID_KEY,
    OAUTH_CARD_SIGNIN_LINK_KEY,
    _build_oauth_adaptive_card,
    _extract_sign_in_link,
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


class _FakeState:
    """Reusable in-memory TurnState substitute for tests."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def set_value(self, key: str, value: object) -> None:
        self._values[key] = value

    def get_value(self, key: str, _type=None) -> object:
        return self._values.get(key)

    def delete_value(self, key: str) -> None:
        self._values.pop(key, None)


def _make_settings(**overrides: str) -> M365Settings:
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


def testbuild_m365_sdk_configuration_uses_settings_values() -> None:
    settings = _make_settings()

    sdk_config = build_m365_sdk_configuration(settings)

    assert sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"]["CLIENTID"] == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"]["TENANTID"] == (
        "22222222-2222-2222-2222-222222222222"
    )


def testbuild_m365_sdk_configuration_raises_for_missing_required_setting() -> None:
    settings = _make_settings(connections_service_connection_client_secret="")

    with pytest.raises(ValueError) as exc:
        build_m365_sdk_configuration(settings)

    assert "connections_service_connection_client_secret" in str(exc.value)


def test_build_oauth_adaptive_card_contains_signin_action() -> None:
    card = _build_oauth_adaptive_card(
        sign_in_link="https://example.com/signin",
        description_text="Sign in to access Fabric.",
    )

    assert card["type"] == "AdaptiveCard"
    assert card["actions"][0]["type"] == "Action.OpenUrl"
    assert card["actions"][0]["url"] == "https://example.com/signin"


def test_build_oauth_adaptive_card_disables_action_when_requested() -> None:
    card = _build_oauth_adaptive_card(
        sign_in_link="https://example.com/signin",
        description_text="Sign in to access Fabric.",
        is_signin_enabled=False,
    )

    assert card["actions"][0]["isEnabled"] is False
    assert card["actions"][0]["title"] == "Sign in opened"


def testextract_magic_code_accepts_numeric_code_only() -> None:
    assert extract_magic_code(" 123456 ") == "123456"
    assert extract_magic_code("not-a-code") is None


def test_extract_sign_in_link_handles_direct_and_nested_shapes() -> None:
    direct = SimpleNamespace(sign_in_link="https://example.com/direct")
    nested = SimpleNamespace(sign_in_resource=SimpleNamespace(sign_in_link="https://example.com/nested"))

    assert _extract_sign_in_link(direct) == "https://example.com/direct"
    assert _extract_sign_in_link(nested) == "https://example.com/nested"


@pytest.mark.asyncio
async def testget_m365_user_token_sends_adaptive_card_when_signin_required(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _make_settings()

    class _FakeState:
        def __init__(self) -> None:
            self._values: dict[str, object] = {}

        def set_value(self, key: str, value: object) -> None:
            self._values[key] = value

        def get_value(self, key: str, _type=None) -> object:
            return self._values.get(key)

        def delete_value(self, key: str) -> None:
            self._values.pop(key, None)

    class _FakeTokenExchangeState:
        def __init__(self, **_kwargs) -> None:
            pass

        def get_encoded_state(self) -> str:
            return "encoded-state"

    monkeypatch.setattr(
        "langgraph_fabric_m365.oauth.TokenExchangeState",
        _FakeTokenExchangeState,
    )

    token_client = SimpleNamespace(
        user_token=SimpleNamespace(
            get_token=AsyncMock(return_value=None),
            _get_token_or_sign_in_resource=AsyncMock(
                return_value=SimpleNamespace(sign_in_link="https://example.com/signin")
            ),
        )
    )
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={"UserTokenClient": token_client},
        activity=SimpleNamespace(
            get_conversation_reference=lambda: SimpleNamespace(
                conversation=SimpleNamespace(id="conv-id")
            ),
            service_url="https://service.example.com",
            relates_to=None,
        ),
        send_activity=AsyncMock(),
        update_activity=AsyncMock(),
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=settings,
        user_id="user-1",
        channel_id="msteams",
    )

    assert token is None
    context.send_activity.assert_awaited_once()
    activity = context.send_activity.await_args.args[0]
    attachment = activity.attachments[0]
    content_type = getattr(attachment, "content_type", None) or attachment["contentType"]
    content = getattr(attachment, "content", None) or attachment["content"]

    assert content_type == "application/vnd.microsoft.card.adaptive"
    assert content["actions"][0]["url"] == "https://example.com/signin"


@pytest.mark.asyncio
async def testget_m365_user_token_redeems_magic_code_and_disables_card(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _make_settings()

    class _FakeState:
        def __init__(self) -> None:
            self._values: dict[str, object] = {
                OAUTH_CARD_ACTIVITY_ID_KEY: "activity-1",
                OAUTH_CARD_SIGNIN_LINK_KEY: "https://example.com/signin",
            }

        def set_value(self, key: str, value: object) -> None:
            self._values[key] = value

        def get_value(self, key: str, _type=None) -> object:
            return self._values.get(key)

        def delete_value(self, key: str) -> None:
            self._values.pop(key, None)

    class _FakeTokenExchangeState:
        def __init__(self, **_kwargs) -> None:
            pass

        def get_encoded_state(self) -> str:
            return "encoded-state"

    monkeypatch.setattr(
        "langgraph_fabric_m365.oauth.TokenExchangeState",
        _FakeTokenExchangeState,
    )

    get_token_mock = AsyncMock(return_value=SimpleNamespace(token="token-from-code"))
    token_client = SimpleNamespace(
        user_token=SimpleNamespace(
            get_token=get_token_mock,
            _get_token_or_sign_in_resource=AsyncMock(),
        )
    )
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={"UserTokenClient": token_client},
        activity=SimpleNamespace(),
        send_activity=AsyncMock(),
        update_activity=AsyncMock(),
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=settings,
        user_id="user-1",
        channel_id="msteams",
        magic_code="123456",
    )

    assert token == "token-from-code"
    assert get_token_mock.await_args.kwargs["code"] == "123456"
    context.update_activity.assert_awaited_once()


# ---------------------------------------------------------------------------
# State helper tests (state_get / state_set / state_delete)
# ---------------------------------------------------------------------------


class _FakeStateWithTemp:
    """Simulates SDK state that exposes a .temp attribute with value accessors."""

    def __init__(self) -> None:
        self._values: dict[str, object] = {}
        self.temp = self  # temp points back to self for simplicity

    def get_value(self, key: str, _type=None) -> object:
        return self._values.get(key)

    def set_value(self, key: str, value: object) -> None:
        self._values[key] = value

    def delete_value(self, key: str) -> None:
        self._values.pop(key, None)


def teststate_get_uses_temp_state_when_available() -> None:
    state = _FakeStateWithTemp()
    state.temp.set_value("foo", "bar")
    assert state_get(state, "foo") == "bar"


def teststate_get_falls_back_to_state_direct() -> None:
    state = _FakeState()
    state.set_value("key1", "val1")
    assert state_get(state, "key1") == "val1"


def teststate_get_returns_none_when_no_get_value_method() -> None:
    invalid_state = SimpleNamespace()
    assert state_get(invalid_state, "key") is None


def teststate_set_uses_temp_state_when_available() -> None:
    state = _FakeStateWithTemp()
    state_set(state, "answer", 42)
    assert state.temp.get_value("answer") == 42


def teststate_set_falls_back_to_state_direct() -> None:
    state = _FakeState()
    state_set(state, "x", "hello")
    assert state.get_value("x") == "hello"


def teststate_delete_uses_temp_state_when_available() -> None:
    state = _FakeStateWithTemp()
    state.temp.set_value("remove_me", "value")
    state_delete(state, "remove_me")
    assert state.temp.get_value("remove_me") is None


def teststate_delete_falls_back_to_state_direct() -> None:
    state = _FakeState()
    state.set_value("to_remove", "value")
    state_delete(state, "to_remove")
    assert state.get_value("to_remove") is None


# ---------------------------------------------------------------------------
# disable_signin_card
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def testdisable_signin_card_updates_activity_with_disabled_card() -> None:
    state = _FakeState()
    state.set_value(OAUTH_CARD_ACTIVITY_ID_KEY, "activity-id-99")
    state.set_value(OAUTH_CARD_SIGNIN_LINK_KEY, "https://example.com/signin")

    context = SimpleNamespace(
        send_activity=AsyncMock(),
        update_activity=AsyncMock(),
    )

    await disable_signin_card(context, state, "Sign-in is in progress.")

    context.update_activity.assert_awaited_once()
    updated = context.update_activity.await_args.args[0]
    # The SDK may wrap the dict as an Attachment object; handle both shapes.
    raw_attachment = updated.attachments[0]
    card_content = (
        getattr(raw_attachment, "content", None) or raw_attachment["content"]
    )
    assert card_content["actions"][0]["isEnabled"] is False


@pytest.mark.asyncio
async def testdisable_signin_card_does_nothing_when_no_activity_id() -> None:
    state = _FakeState()  # no IDs stored

    context = SimpleNamespace(update_activity=AsyncMock())
    await disable_signin_card(context, state, "Some message")

    context.update_activity.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_m365_user_token - additional paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def testget_m365_user_token_returns_none_when_no_token_client() -> None:
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={},  # no client registered
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=_make_settings(),
        user_id="u1",
        channel_id="msteams",
    )
    assert token is None


@pytest.mark.asyncio
async def testget_m365_user_token_returns_none_when_no_channel_id() -> None:
    token_client = SimpleNamespace(user_token=SimpleNamespace(get_token=AsyncMock()))
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={"UserTokenClient": token_client},
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=_make_settings(),
        user_id="u1",
        channel_id=None,  # no channel id
    )
    assert token is None


@pytest.mark.asyncio
async def testget_m365_user_token_handles_404_and_prompts_signin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 404 from the token service should trigger the sign-in flow."""
    settings = _make_settings()

    class _FakeTokenExchangeState:
        def __init__(self, **_kwargs) -> None:
            pass

        def get_encoded_state(self) -> str:
            return "encoded-state"

    monkeypatch.setattr("langgraph_fabric_m365.oauth.TokenExchangeState", _FakeTokenExchangeState)

    error_404 = ClientResponseError(None, None)
    error_404.status = 404

    token_client = SimpleNamespace(
        user_token=SimpleNamespace(
            get_token=AsyncMock(side_effect=error_404),
            _get_token_or_sign_in_resource=AsyncMock(
                return_value=SimpleNamespace(sign_in_link="https://example.com/signin")
            ),
        )
    )
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={"UserTokenClient": token_client},
        activity=SimpleNamespace(
            get_conversation_reference=lambda: SimpleNamespace(
                conversation=SimpleNamespace(id="conv-1")
            ),
            service_url="https://service.example.com",
            relates_to=None,
        ),
        send_activity=AsyncMock(),
        update_activity=AsyncMock(),
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=settings,
        user_id="u1",
        channel_id="msteams",
    )

    assert token is None
    context.send_activity.assert_awaited_once()


@pytest.mark.asyncio
async def testget_m365_user_token_handles_value_error_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ValueError from the token lookup should not propagate."""
    settings = _make_settings()

    token_client = SimpleNamespace(
        user_token=SimpleNamespace(
            get_token=AsyncMock(side_effect=ValueError("invalid context")),
        )
    )
    context = SimpleNamespace(
        adapter=SimpleNamespace(USER_TOKEN_CLIENT_KEY="UserTokenClient"),
        turn_state={"UserTokenClient": token_client},
        activity=SimpleNamespace(),
        send_activity=AsyncMock(),
        update_activity=AsyncMock(),
    )
    state = _FakeState()

    token = await get_m365_user_token(
        context=context,
        state=state,
        settings=settings,
        user_id="u1",
        channel_id="msteams",
    )

    assert token is None


# ---------------------------------------------------------------------------
# build_m365_environment
# ---------------------------------------------------------------------------


def testbuild_m365_environment_includes_all_required_settings_keys() -> None:
    settings = _make_settings()
    env = build_m365_environment(settings)

    assert env["MICROSOFT_APP_ID"] == settings.microsoft_app_id
    assert env["MICROSOFT_APP_PASSWORD"] == settings.microsoft_app_password
    assert env["MICROSOFT_TENANT_ID"] == settings.microsoft_tenant_id
    assert env["FABRIC_OAUTH_CONNECTION_NAME"] == settings.fabric_oauth_connection_name
    assert env["CONNECTIONS__SERVICE_CONNECTION__ID"] == settings.connections_service_connection_id
    assert (
        env["CONNECTIONS__SERVICE_CONNECTION__NAME"]
        == settings.connections_service_connection_name
    )
    assert (
        env["CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"]
        == settings.connections_service_connection_client_id
    )


def testbuild_m365_environment_returns_dict_containing_os_env(monkeypatch) -> None:
    """build_m365_environment merges OS env into the output dict."""
    monkeypatch.setenv("TEST_UNIQUE_MARKER_VAR", "marker-value")
    settings = _make_settings()
    env = build_m365_environment(settings)
    assert env.get("TEST_UNIQUE_MARKER_VAR") == "marker-value"
