"""Console-specific configuration settings."""

from functools import lru_cache

from langgraph_fabric_core.core.config import CoreSettings
from pydantic_settings import SettingsConfigDict


class ConsoleSettings(CoreSettings):
    """Settings for the interactive terminal console.

    Extends CoreSettings with console-specific env_file. The optional
    `microsoft_app_id` and `microsoft_tenant_id` from CoreSettings are
    available for device-code credential fallback when running locally.
    Reads from `.env.console` in addition to environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env.console",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> ConsoleSettings:
    """Return cached console settings."""
    return ConsoleSettings()
