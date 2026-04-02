"""M365-specific configuration settings."""

from functools import lru_cache
from pathlib import Path

from langgraph_fabric_core.core.config import CoreSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict

_ENV_FILE = Path(__file__).parents[2] / ".env"


class M365Settings(CoreSettings):
    """Settings for the M365 Agents SDK adapter (Teams / Copilot Chat).

    Extends CoreSettings with fields required for the M365 bot authentication,
    Bot Service OAuth connection, and M365 Agents SDK service connection.
    Reads from `.env` in the package directory.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    microsoft_app_id: str = Field(alias="MICROSOFT_APP_ID")
    microsoft_app_password: str = Field(alias="MICROSOFT_APP_PASSWORD")
    microsoft_tenant_id: str = Field(alias="MICROSOFT_TENANT_ID")

    connections_service_connection_id: str = Field(
        default="", alias="CONNECTIONS__SERVICE_CONNECTION__ID"
    )
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


@lru_cache(maxsize=1)
def get_settings() -> M365Settings:
    """Return cached M365 settings."""
    return M365Settings()
