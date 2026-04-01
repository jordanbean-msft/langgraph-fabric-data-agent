from types import SimpleNamespace

import pytest
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError
from langgraph_fabric_core.core.config import AppSettings
from langgraph_fabric_core.fabric.auth import AuthContext, FabricTokenProvider


@pytest.fixture(name="settings_fixture")
def settings_fixture_data(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    return AppSettings()


@pytest.mark.asyncio
async def test_hosted_mode_requires_token(settings_fixture):
    provider = FabricTokenProvider(settings_fixture)
    context = AuthContext(mode="hosted", user_id="u1", hosted_user_token=None)
    with pytest.raises(ValueError):
        await provider.get_token(context)


@pytest.mark.asyncio
async def test_local_mode_falls_back_to_device_code(settings_fixture):
    provider = FabricTokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(ClientAuthenticationError("x"))
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token="device-token")
        ),
    )

    token = await provider.get_token(AuthContext(mode="local", user_id="u1"))
    assert token == "device-token"


@pytest.mark.asyncio
async def test_local_mode_falls_back_to_device_code_when_default_credential_is_unavailable(settings_fixture):
    provider = FabricTokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(CredentialUnavailableError("x"))
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token="device-token")
        ),
    )

    token = await provider.get_token(AuthContext(mode="local", user_id="u1"))
    assert token == "device-token"
