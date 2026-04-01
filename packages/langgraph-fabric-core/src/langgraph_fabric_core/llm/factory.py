"""LLM factory for Azure OpenAI / Foundry."""

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI

from langgraph_fabric_core.core.config import AppSettings

_FOUNDRY_PROJECT_API_VERSION = "2025-11-15-preview"


def _is_foundry_project_endpoint(endpoint: str) -> bool:
    return "/api/projects/" in endpoint


def _resolve_api_version(settings: AppSettings) -> str:
    if not _is_foundry_project_endpoint(settings.azure_openai_endpoint):
        return settings.azure_openai_api_version

    if settings.azure_openai_api_version in {"preview", "2024-10-21"}:
        return _FOUNDRY_PROJECT_API_VERSION

    return settings.azure_openai_api_version


def _use_previous_response_id(settings: AppSettings) -> bool:
    """Return whether response ID chaining should be enabled."""
    # LangGraph tool loops send function-call outputs as message inputs; for
    # Foundry project endpoints this is more reliable without response ID chaining.
    return not _is_foundry_project_endpoint(settings.azure_openai_endpoint)


def create_chat_model(settings: AppSettings) -> AzureChatOpenAI:
    """Create the chat model used by LangGraph."""
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        settings.azure_openai_scope,
    )
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=_resolve_api_version(settings),
        azure_ad_token_provider=token_provider,
        temperature=0,
        streaming=True,
        use_responses_api=_is_foundry_project_endpoint(settings.azure_openai_endpoint),
        use_previous_response_id=_use_previous_response_id(settings),
        output_version="responses/v1",
    )
