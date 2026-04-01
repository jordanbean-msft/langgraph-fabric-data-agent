"""Application configuration models."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Centralized environment-backed settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_level_override: str | None = Field(default=None, alias="LOG_LEVEL_OVERRIDE")
    port: int = Field(default=8000, alias="PORT")

    azure_openai_endpoint: str = Field(alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment_name: str = Field(alias="AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME")
    azure_openai_api_version: str = Field(default="2025-11-15-preview", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_scope: str = Field(default="https://ai.azure.com/.default", alias="AZURE_OPENAI_SCOPE")

    fabric_data_agent_mcp_url: str = Field(alias="FABRIC_DATA_AGENT_MCP_URL")
    fabric_data_agent_scope: str = Field(
        default="https://api.fabric.microsoft.com/.default",
        alias="FABRIC_DATA_AGENT_SCOPE",
    )
    fabric_data_agent_timeout_seconds: int = Field(default=120, alias="FABRIC_DATA_AGENT_TIMEOUT_SECONDS")
    fabric_data_agent_poll_interval_seconds: int = Field(
        default=2,
        alias="FABRIC_DATA_AGENT_POLL_INTERVAL_SECONDS",
    )

    microsoft_app_id: str = Field(default="", alias="MICROSOFT_APP_ID")
    microsoft_app_password: str = Field(default="", alias="MICROSOFT_APP_PASSWORD")
    microsoft_tenant_id: str = Field(default="", alias="MICROSOFT_TENANT_ID")
    fabric_oauth_connection_name: str = Field(default="FabricOAuth2", alias="FABRIC_OAUTH_CONNECTION_NAME")

    connections_service_connection_id: str = Field(default="", alias="CONNECTIONS__SERVICE_CONNECTION__ID")
    connections_service_connection_name: str = Field(
        default="",
        alias="CONNECTIONS__SERVICE_CONNECTION__NAME",
    )
    connections_service_connection_client_id: str = Field(
        default="",
        alias="CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID",
    )
    connections_service_connection_tenant_id: str = Field(
        default="",
        alias="CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID",
    )
    connections_service_connection_auth_type: str = Field(
        default="",
        alias="CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE",
    )
    connections_service_connection_client_secret: str = Field(
        default="",
        alias="CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET",
    )

    @field_validator("log_level_override", mode="before")
    @classmethod
    def normalize_log_level_override(cls, value: str | None) -> str | None:
        """Treat blank LOG_LEVEL_OVERRIDE values as unset."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings."""
    return AppSettings()
