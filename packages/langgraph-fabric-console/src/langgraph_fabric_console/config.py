"""Console-specific configuration settings."""

from functools import lru_cache
from pathlib import Path

from langgraph_fabric_core.core.config import CoreSettings
from pydantic_settings import SettingsConfigDict

_ENV_FILE = Path(__file__).parents[2] / ".env"


class ConsoleSettings(CoreSettings):
    """Settings for the interactive terminal console.

    Extends CoreSettings with console-specific env_file. The optional
    `microsoft_app_id` and `microsoft_tenant_id` from CoreSettings are
    available for device-code credential fallback when running locally.
    Reads from `.env` in the package directory.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> ConsoleSettings:
    """Return cached console settings."""
    return ConsoleSettings()
