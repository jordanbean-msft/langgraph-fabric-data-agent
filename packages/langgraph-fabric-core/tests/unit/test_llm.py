from unittest.mock import sentinel

from langgraph_fabric_core.llm.factory import create_chat_model


def test_create_chat_model_uses_foundry_project_scope(monkeypatch, settings_fixture):
    captured: dict[str, object] = {}

    def fake_default_credential():
        return sentinel.credential

    def fake_get_bearer_token_provider(credential, scope):
        captured["credential"] = credential
        captured["scope"] = scope
        return sentinel.token_provider

    class FakeAzureChatOpenAI:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr("langgraph_fabric_core.llm.factory.DefaultAzureCredential", fake_default_credential)
    monkeypatch.setattr(
        "langgraph_fabric_core.llm.factory.get_bearer_token_provider",
        fake_get_bearer_token_provider,
    )
    monkeypatch.setattr("langgraph_fabric_core.llm.factory.AzureChatOpenAI", FakeAzureChatOpenAI)

    create_chat_model(settings_fixture)

    assert captured["credential"] is sentinel.credential
    assert captured["scope"] == "https://ai.azure.com/.default"
    assert captured["kwargs"]["azure_endpoint"] == settings_fixture.azure_openai_endpoint
    assert captured["kwargs"]["azure_deployment"] == settings_fixture.azure_openai_deployment_name
    assert captured["kwargs"]["api_version"] == "2025-11-15-preview"
    assert captured["kwargs"]["azure_ad_token_provider"] is sentinel.token_provider
    assert captured["kwargs"]["use_responses_api"] is True
    assert captured["kwargs"]["use_previous_response_id"] is False
    assert captured["kwargs"]["output_version"] == "responses/v1"


def test_create_chat_model_normalizes_legacy_project_api_versions(monkeypatch, settings_fixture):
    captured: dict[str, object] = {}

    def fake_default_credential():
        return sentinel.credential

    def fake_get_bearer_token_provider(credential, scope):
        captured["credential"] = credential
        captured["scope"] = scope
        return sentinel.token_provider

    class FakeAzureChatOpenAI:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    settings_fixture.azure_openai_api_version = "preview"

    monkeypatch.setattr("langgraph_fabric_core.llm.factory.DefaultAzureCredential", fake_default_credential)
    monkeypatch.setattr(
        "langgraph_fabric_core.llm.factory.get_bearer_token_provider",
        fake_get_bearer_token_provider,
    )
    monkeypatch.setattr("langgraph_fabric_core.llm.factory.AzureChatOpenAI", FakeAzureChatOpenAI)

    create_chat_model(settings_fixture)

    assert captured["kwargs"]["api_version"] == "2025-11-15-preview"
    assert captured["kwargs"]["use_previous_response_id"] is False


def test_create_chat_model_uses_previous_response_id_for_non_project_endpoints(
    monkeypatch,
    settings_fixture,
):
    captured: dict[str, object] = {}

    def fake_default_credential():
        return sentinel.credential

    def fake_get_bearer_token_provider(credential, scope):
        captured["credential"] = credential
        captured["scope"] = scope
        return sentinel.token_provider

    class FakeAzureChatOpenAI:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    settings_fixture.azure_openai_endpoint = "https://example.openai.azure.com"
    settings_fixture.azure_openai_api_version = "2024-10-21"

    monkeypatch.setattr("langgraph_fabric_core.llm.factory.DefaultAzureCredential", fake_default_credential)
    monkeypatch.setattr(
        "langgraph_fabric_core.llm.factory.get_bearer_token_provider",
        fake_get_bearer_token_provider,
    )
    monkeypatch.setattr("langgraph_fabric_core.llm.factory.AzureChatOpenAI", FakeAzureChatOpenAI)

    create_chat_model(settings_fixture)

    assert captured["kwargs"]["api_version"] == "2024-10-21"
    assert captured["kwargs"]["use_responses_api"] is False
    assert captured["kwargs"]["use_previous_response_id"] is True
