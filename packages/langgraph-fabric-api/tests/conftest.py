"""Shared fixtures for langgraph-fabric-api tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _clear_orchestrator_cache():
    """Clear get_orchestrator cache before and after each test.

    This ensures each test gets a fresh orchestrator instance,
    preventing cache pollution from dependency overrides.
    """
    from langgraph_fabric_api.core.dependencies import get_orchestrator

    get_orchestrator.cache_clear()
    yield
    get_orchestrator.cache_clear()


@pytest.fixture()
def fake_settings() -> MagicMock:
    """Minimal ApiSettings-compatible mock for tests that do not need real env vars."""
    settings = MagicMock()
    settings.microsoft_app_id = "test-app-id"
    settings.microsoft_app_password = "test-secret"
    settings.microsoft_tenant_id = "test-tenant"
    settings.mcp_servers = [
        SimpleNamespace(
            name="fabric",
            scope="https://api.fabric.microsoft.com/.default",
            description="Fabric MCP",
            url="https://api.fabric.microsoft.com/v1/mcp/demo",
            oauth_connection_name="FabricOAuth2",
            timeout_seconds=120,
            poll_interval_seconds=2,
        )
    ]
    return settings
