import pytest
from langgraph_fabric_core.core.config import CoreSettings


@pytest.fixture
def settings_fixture(monkeypatch):
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo"
    )
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv(
        "MCP_SERVERS",
        '[{"name":"fabric","description":"Fabric MCP","url":"https://api.fabric.microsoft.com/v1/mcp/demo","scope":"https://api.fabric.microsoft.com/.default","oauth_connection_name":"FabricOAuth2"}]',
    )
    return CoreSettings()


@pytest.fixture
def server_config_fixture(request):
    settings = request.getfixturevalue("settings_fixture")
    return settings.mcp_servers[0]
