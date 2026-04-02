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


def test_streaming_endpoint_obo_token_reaches_orchestrator(monkeypatch, fake_settings):
    """Integration: the fabric token from OBO exchange reaches orchestrator.stream()."""
    captured: dict = {}

    class CapturingOrchestrator:
        async def stream(self, **kwargs) -> AsyncIterator[str]:
            captured.update(kwargs)
            yield "response"

    async def capturing_obo(bearer_token: str, settings) -> str:
        return "obo-fabric-token"

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: CapturingOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", capturing_obo)
    client = TestClient(api_module.app)
    client.post(
        "/chat/stream",
        json={"prompt": "query"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )

    assert captured.get("fabric_user_token") == "obo-fabric-token"
    assert captured.get("auth_mode") == "hosted"
    assert captured.get("channel") == "api"


def test_streaming_endpoint_returns_422_when_prompt_is_missing(monkeypatch, fake_settings):
    """Integration: ChatRequest rejects requests that omit the required `prompt` field."""
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", _fake_obo)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={},
        headers={"Authorization": "Bearer fake-caller-token"},
    )
    assert response.status_code == 422


def test_streaming_endpoint_sse_format_includes_data_prefix(monkeypatch, fake_settings):
    """Integration: each yielded chunk is formatted as an SSE data line."""

    class SseOrchestrator:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "test chunk"

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", lambda: SseOrchestrator())
    monkeypatch.setattr(api_module, "_get_fabric_token_obo", _fake_obo)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "p"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )

    assert "data: test chunk" in response.text
    assert "event: done" in response.text
