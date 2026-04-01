import pytest

from langgraph_fabric_data_agent.config import AppSettings


@pytest.fixture
def settings_fixture(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    return AppSettings()
