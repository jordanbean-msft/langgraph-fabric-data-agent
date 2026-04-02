import importlib
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

api_module = importlib.import_module("langgraph_fabric_api.app")


class FakeOrchestrator:
    async def stream(self, **_kwargs) -> AsyncIterator[str]:
        yield "chunk-1"
        yield "chunk-2"


async def _fake_obo(bearer_token: str, settings) -> str:
    return "fake-fabric-token"


def test_streaming_endpoint(monkeypatch, fake_settings):
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", _fake_obo)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "hello"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )
    assert response.status_code == 200
    assert "chunk-1" in response.text
    assert "chunk-2" in response.text
    assert "[DONE]" in response.text


def test_streaming_endpoint_no_auth_returns_401(monkeypatch, fake_settings):
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", _fake_obo)
    client = TestClient(api_module.app, raise_server_exceptions=False)
    response = client.post("/chat/stream", json={"prompt": "hello"})
    assert response.status_code == 401
