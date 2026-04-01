from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from langgraph_fabric_data_agent.core.config import AppSettings
from langgraph_fabric_data_agent.hosted.oauth import (
    OAUTH_CARD_ACTIVITY_ID_KEY,
    OAUTH_CARD_SIGNIN_LINK_KEY,
    _build_oauth_adaptive_card,
    _extract_magic_code,
    _extract_sign_in_link,
    _get_hosted_user_token,
)
from langgraph_fabric_data_agent.hosted.runtime import _build_hosted_sdk_configuration


def _make_settings(**overrides: str) -> AppSettings:
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
    return AppSettings.model_construct(**base)


def test_build_hosted_sdk_configuration_uses_settings_values() -> None:
    settings = _make_settings()

    sdk_config = _build_hosted_sdk_configuration(settings)

    assert sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"]["CLIENTID"] == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert sdk_config["CONNECTIONS"]["SERVICE_CONNECTION"]["SETTINGS"]["TENANTID"] == (
        "22222222-2222-2222-2222-222222222222"
    )


def test_build_hosted_sdk_configuration_raises_for_missing_required_setting() -> None:
    settings = _make_settings(connections_service_connection_client_secret="")

    with pytest.raises(ValueError) as exc:
        _build_hosted_sdk_configuration(settings)

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


def test_extract_magic_code_accepts_numeric_code_only() -> None:
    assert _extract_magic_code(" 123456 ") == "123456"
    assert _extract_magic_code("not-a-code") is None


def test_extract_sign_in_link_handles_direct_and_nested_shapes() -> None:
    direct = SimpleNamespace(sign_in_link="https://example.com/direct")
    nested = SimpleNamespace(sign_in_resource=SimpleNamespace(sign_in_link="https://example.com/nested"))

    assert _extract_sign_in_link(direct) == "https://example.com/direct"
    assert _extract_sign_in_link(nested) == "https://example.com/nested"


@pytest.mark.asyncio
async def test_get_hosted_user_token_sends_adaptive_card_when_signin_required(monkeypatch: pytest.MonkeyPatch) -> None:
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
        "langgraph_fabric_data_agent.hosted.oauth.TokenExchangeState",
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

    token = await _get_hosted_user_token(
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
async def test_get_hosted_user_token_redeems_magic_code_and_disables_card(monkeypatch: pytest.MonkeyPatch) -> None:
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
        "langgraph_fabric_data_agent.hosted.oauth.TokenExchangeState",
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

    token = await _get_hosted_user_token(
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
