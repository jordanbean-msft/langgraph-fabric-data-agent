from types import SimpleNamespace

import pytest
from azure.core.exceptions import ClientAuthenticationError

from langgraph_fabric_data_agent.auth import AuthContext, FabricTokenProvider
from langgraph_fabric_data_agent.config import AppSettings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    return AppSettings()


@pytest.mark.asyncio
async def test_hosted_mode_requires_token(settings):
    provider = FabricTokenProvider(settings)
    context = AuthContext(mode="hosted", user_id="u1", hosted_user_token=None)
    with pytest.raises(ValueError):
        await provider.get_token(context)


@pytest.mark.asyncio
async def test_local_mode_falls_back_to_device_code(settings):
    provider = FabricTokenProvider(settings)
    provider._default_credential = SimpleNamespace(
        get_token=lambda _scope: (_ for _ in ()).throw(ClientAuthenticationError("x"))
    )
    provider._device_code_credential = SimpleNamespace(
        get_token=lambda _scope: SimpleNamespace(token="device-token")
    )

    token = await provider.get_token(AuthContext(mode="local", user_id="u1"))
    assert token == "device-token"
