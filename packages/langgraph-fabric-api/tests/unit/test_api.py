from fastapi.testclient import TestClient
from langgraph_fabric_api.app import app
from langgraph_fabric_api.core.auth import extract_user_id, get_token_obo


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_stream_missing_auth_header_returns_401():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/chat/stream", json={"prompt": "hello"})
    assert response.status_code == 401


def test_chat_stream_still_requires_auth_header_in_chat_only_mode(fake_settings):
    from langgraph_fabric_api.config import get_settings as original_get_settings
    from langgraph_fabric_api.core.dependencies import get_orchestrator

    fake_settings.mcp_servers = []

    def get_fake_settings():
        return fake_settings

    def get_fake_orchestrator():
        from collections.abc import AsyncIterator

        class FakeOrchestrator:
            async def stream(self, **_kwargs) -> AsyncIterator[str]:
                yield "response"

        return FakeOrchestrator()

    app.dependency_overrides[original_get_settings] = get_fake_settings
    app.dependency_overrides[get_orchestrator] = get_fake_orchestrator

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/chat/stream", json={"prompt": "hello"})
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_extract_user_id_preferred_username():
    # JWT payload: {"preferred_username": "alice@example.com", "sub": "abc123"}
    token = "header.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiAiYWxpY2VAZXhhbXBsZS5jb20iLCAic3ViIjogImFiYzEyMyJ9.sig"
    assert extract_user_id(token) == "alice@example.com"


def test_extract_user_id_falls_back_to_sub():
    # JWT payload: {"sub": "abc123"}
    token = "header.eyJzdWIiOiAiYWJjMTIzIn0.sig"
    assert extract_user_id(token) == "abc123"


def test_extract_user_id_invalid_token():
    assert extract_user_id("not-a-jwt") == "unknown"


def test_chat_stream_streams_with_mocked_obo(monkeypatch, fake_settings):
    """OBO exchange is mocked; endpoint should stream chunks and [DONE]."""
    from collections.abc import AsyncIterator

    from langgraph_fabric_api.config import get_settings as original_get_settings
    from langgraph_fabric_api.core.dependencies import get_orchestrator

    class FakeOrchestrator:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "\n[tool] Querying mcp_fabric...\n"
            yield "chunk-1"
            yield "chunk-2"

    def get_fake_orchestrator() -> FakeOrchestrator:
        return FakeOrchestrator()

    def get_fake_settings():
        return fake_settings

    app.dependency_overrides[original_get_settings] = get_fake_settings
    app.dependency_overrides[get_orchestrator] = get_fake_orchestrator

    async def fake_obo(_bearer_token: str, _settings, scope: str) -> str:
        assert scope == "https://api.fabric.microsoft.com/.default"
        return "fake-fabric-token"

    monkeypatch.setattr("langgraph_fabric_api.routes.chat.get_token_obo", fake_obo)

    try:
        client = TestClient(app)
        response = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            headers={"Authorization": "Bearer fake-caller-token"},
        )
        assert response.status_code == 200
        assert "event: tool_status" in response.text
        assert "[tool] Querying mcp_fabric..." in response.text
        assert "event: text" in response.text
        assert "chunk-1" in response.text
        assert "chunk-2" in response.text
        assert "[DONE]" in response.text
    finally:
        app.dependency_overrides.clear()


def test_get_token_obo_missing_app_id_returns_500(fake_settings):
    """When MICROSOFT_APP_ID is missing, OBO should raise HTTP 500."""
    import pytest

    fake_settings.microsoft_app_id = ""
    fake_settings.microsoft_app_password = "secret"
    fake_settings.microsoft_tenant_id = "tenant"

    with pytest.raises(Exception) as exc_info:
        # Note: sync wrapper for async test
        import asyncio

        asyncio.run(get_token_obo("bearer", fake_settings, "scope"))
    assert "500" in str(exc_info.value) or "not configured" in str(exc_info.value).lower()


def test_get_token_obo_missing_password_returns_500(fake_settings):
    """When MICROSOFT_APP_PASSWORD is missing, OBO should raise HTTP 500."""
    import pytest

    fake_settings.microsoft_app_id = "app-id"
    fake_settings.microsoft_app_password = ""
    fake_settings.microsoft_tenant_id = "tenant"

    with pytest.raises(Exception) as exc_info:
        import asyncio

        asyncio.run(get_token_obo("bearer", fake_settings, "scope"))
    assert "500" in str(exc_info.value) or "not configured" in str(exc_info.value).lower()


def test_get_token_obo_missing_tenant_returns_500(fake_settings):
    """When MICROSOFT_TENANT_ID is missing, OBO should raise HTTP 500."""
    import pytest

    fake_settings.microsoft_app_id = "app-id"
    fake_settings.microsoft_app_password = "secret"
    fake_settings.microsoft_tenant_id = ""

    with pytest.raises(Exception) as exc_info:
        import asyncio

        asyncio.run(get_token_obo("bearer", fake_settings, "scope"))
    assert "500" in str(exc_info.value) or "not configured" in str(exc_info.value).lower()


def test_chat_stream_obo_auth_error_returns_401(monkeypatch, fake_settings):
    """When OBO exchange fails with ClientAuthenticationError, returns HTTP 401."""
    from azure.core.exceptions import ClientAuthenticationError
    from langgraph_fabric_api.config import get_settings as original_get_settings
    from langgraph_fabric_api.core.dependencies import get_orchestrator

    def get_fake_settings():
        return fake_settings

    def get_fake_orchestrator():
        from collections.abc import AsyncIterator

        class FakeOrchestrator:
            async def stream(self, **_kwargs) -> AsyncIterator[str]:
                yield "response"

        return FakeOrchestrator()

    app.dependency_overrides[original_get_settings] = get_fake_settings
    app.dependency_overrides[get_orchestrator] = get_fake_orchestrator

    class FakeOnBehalfOfCredential:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_token(self, _scope: str):
            raise ClientAuthenticationError("Invalid token")

    monkeypatch.setattr(
        "langgraph_fabric_api.core.auth.OnBehalfOfCredential",
        FakeOnBehalfOfCredential,
    )

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            headers={"Authorization": "Bearer fake-caller-token"},
        )
        assert response.status_code == 401
        assert "Token exchange failed" in response.text
    finally:
        app.dependency_overrides.clear()


def test_chat_stream_token_deduplication_by_scope(monkeypatch, fake_settings):
    """Multiple servers with same scope should only acquire one token."""
    from collections.abc import AsyncIterator
    from types import SimpleNamespace

    from langgraph_fabric_api.core.dependencies import get_orchestrator

    # Create two servers with the same scope
    fake_settings.mcp_servers = [
        SimpleNamespace(
            name="fabric1",
            scope="https://api.fabric.microsoft.com/.default",
            description="Fabric MCP 1",
            url="https://api.fabric.microsoft.com/v1",
            oauth_connection_name="FabricOAuth2",
            timeout_seconds=120,
            poll_interval_seconds=2,
        ),
        SimpleNamespace(
            name="fabric2",
            scope="https://api.fabric.microsoft.com/.default",  # Same scope
            description="Fabric MCP 2",
            url="https://api.fabric.microsoft.com/v2",
            oauth_connection_name="FabricOAuth2",
            timeout_seconds=120,
            poll_interval_seconds=2,
        ),
    ]

    obo_call_count = 0
    received_mcp_tokens = {}

    async def counting_obo(_bearer_token: str, _settings, _scope: str) -> str:
        nonlocal obo_call_count
        obo_call_count += 1
        return "token-123"

    class FakeOrchestrator:
        async def stream(self, **kwargs) -> AsyncIterator[str]:
            # Capture tokens for assertion
            nonlocal received_mcp_tokens
            received_mcp_tokens = kwargs.get("mcp_user_tokens", {})
            yield "response"

    def get_capturing_orchestrator():
        return FakeOrchestrator()

    app.dependency_overrides[get_orchestrator] = get_capturing_orchestrator
    monkeypatch.setattr("langgraph_fabric_api.routes.chat.get_settings", lambda: fake_settings)
    monkeypatch.setattr("langgraph_fabric_api.routes.chat.get_token_obo", counting_obo)

    try:
        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"prompt": "hello"},
            headers={"Authorization": "Bearer fake-caller-token"},
        )

        # Should only call OBO once since both servers share the scope
        assert obo_call_count == 1, f"Expected 1 OBO call, got {obo_call_count}"
        # Both servers should have the same token
        assert "fabric1" in received_mcp_tokens, (
            f"Expected fabric1 in tokens, got: {list(received_mcp_tokens.keys())}"
        )
        assert received_mcp_tokens["fabric1"] == "token-123"
        assert received_mcp_tokens["fabric2"] == "token-123"
    finally:
        app.dependency_overrides.clear()
