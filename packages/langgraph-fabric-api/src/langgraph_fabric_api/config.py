"""API-specific configuration settings."""

from functools import lru_cache
from pathlib import Path

from langgraph_fabric_core.core.config import CoreSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict

_ENV_FILE = Path(__file__).parents[2] / ".env"


class ApiSettings(CoreSettings):
    """Settings for the FastAPI server.

    Extends CoreSettings with fields required for the On-Behalf-Of (OBO)
    token exchange used to obtain scope-specific MCP tokens from the caller's JWT.
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


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    """Return cached API settings."""
    return ApiSettings()
