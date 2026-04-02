import importlib

from fastapi.testclient import TestClient
from langgraph_fabric_api.app import _extract_user_id, app

api_module = importlib.import_module("langgraph_fabric_api.app")


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_stream_missing_auth_header_returns_401():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/chat/stream", json={"prompt": "hello"})
    assert response.status_code == 401


def test_extract_user_id_preferred_username():
    # JWT payload: {"preferred_username": "alice@example.com", "sub": "abc123"}
    token = "header.eyJwcmVmZXJyZWRfdXNlcm5hbWUiOiAiYWxpY2VAZXhhbXBsZS5jb20iLCAic3ViIjogImFiYzEyMyJ9.sig"
    assert _extract_user_id(token) == "alice@example.com"


def test_extract_user_id_falls_back_to_sub():
    # JWT payload: {"sub": "abc123"}
    token = "header.eyJzdWIiOiAiYWJjMTIzIn0.sig"
    assert _extract_user_id(token) == "abc123"


def test_extract_user_id_invalid_token():
    assert _extract_user_id("not-a-jwt") == "unknown"


def test_chat_stream_streams_with_mocked_obo(monkeypatch, fake_settings):
    """OBO exchange is mocked; endpoint should stream chunks and [DONE]."""
    from collections.abc import AsyncIterator

    class FakeOrchestrator:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "\n[tool] Querying Fabric Data Agent...\n"
            yield "chunk-1"
            yield "chunk-2"

    async def fake_obo(bearer_token: str, settings) -> str:
        return "fake-fabric-token"

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", fake_obo)

    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "hello"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )
    assert response.status_code == 200
    assert "event: tool_status" in response.text
    assert "[tool] Querying Fabric Data Agent..." in response.text
    assert "event: text" in response.text
    assert "chunk-1" in response.text
    assert "chunk-2" in response.text
    assert "[DONE]" in response.text
