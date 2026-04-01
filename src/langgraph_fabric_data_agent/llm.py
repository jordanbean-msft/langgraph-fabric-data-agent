"""LLM factory for Azure OpenAI / Foundry."""

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI

from langgraph_fabric_data_agent.config import AppSettings


def create_chat_model(settings: AppSettings) -> AzureChatOpenAI:
    """Create the chat model used by LangGraph."""
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        azure_ad_token_provider=token_provider,
        temperature=0,
        streaming=True,
    )
