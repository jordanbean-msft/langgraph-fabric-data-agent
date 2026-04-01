from langgraph_fabric_data_agent.config import AppSettings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")

    settings = AppSettings()

    assert settings.azure_openai_deployment_name == "gpt-5.4"
    assert settings.fabric_data_agent_scope == "https://api.fabric.microsoft.com/.default"
