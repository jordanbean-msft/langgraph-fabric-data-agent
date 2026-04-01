import pytest
from langgraph_fabric_core.core.config import AppSettings


@pytest.fixture
def settings_fixture(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    return AppSettings()
