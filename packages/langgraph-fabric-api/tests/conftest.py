"""Shared fixtures for langgraph-fabric-api tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def fake_settings() -> MagicMock:
    """Minimal ApiSettings-compatible mock for tests that do not need real env vars."""
    settings = MagicMock()
    settings.microsoft_app_id = "test-app-id"
    settings.microsoft_app_password = "test-secret"
    settings.microsoft_tenant_id = "test-tenant"
    settings.fabric_data_agent_scope = "https://api.fabric.microsoft.com/.default"
    return settings
