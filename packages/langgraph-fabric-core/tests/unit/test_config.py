from langgraph_fabric_core.core.config import AppSettings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")

    settings = AppSettings()

    assert settings.azure_openai_deployment_name == "gpt-5.4"
    assert settings.azure_openai_api_version == "2025-11-15-preview"
    assert settings.azure_openai_scope == "https://ai.azure.com/.default"
    assert settings.fabric_data_agent_scope == "https://api.fabric.microsoft.com/.default"
    assert settings.log_level_override is None


def test_settings_load_log_level_override(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    monkeypatch.setenv(
        "LOG_LEVEL_OVERRIDE",
        "langgraph_fabric_core.graph:DEBUG,azure.core:WARNING",
    )

    settings = AppSettings()

    assert settings.log_level_override == "langgraph_fabric_core.graph:DEBUG,azure.core:WARNING"


def test_settings_empty_log_level_override_is_none(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo")
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("FABRIC_DATA_AGENT_MCP_URL", "https://api.fabric.microsoft.com/v1/mcp/demo")
    monkeypatch.setenv("LOG_LEVEL_OVERRIDE", "")

    settings = AppSettings()

    assert settings.log_level_override is None
