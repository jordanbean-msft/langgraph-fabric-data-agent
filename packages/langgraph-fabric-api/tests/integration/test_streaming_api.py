import importlib
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

api_module = importlib.import_module("langgraph_fabric_api.app")


class FakeOrchestrator:
    async def stream(self, **_kwargs) -> AsyncIterator[str]:
        yield "chunk-1"
        yield "chunk-2"


def test_streaming_endpoint(monkeypatch):
    def fake_get_orchestrator() -> FakeOrchestrator:
        return FakeOrchestrator()

    monkeypatch.setattr(api_module, "get_orchestrator", fake_get_orchestrator)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "hello", "auth_mode": "local", "user_id": "u1"},
    )
    assert response.status_code == 200
    assert "chunk-1" in response.text
    assert "chunk-2" in response.text
    assert "[DONE]" in response.text


def test_streaming_endpoint_passes_fabric_user_token_to_orchestrator(monkeypatch):
    """Integration: fabric_user_token from the request reaches orchestrator.stream()."""
    captured: dict = {}

    class CapturingOrchestrator:
        async def stream(self, **kwargs) -> AsyncIterator[str]:
            captured.update(kwargs)
            yield "response"

    monkeypatch.setattr(api_module, "get_orchestrator", lambda: CapturingOrchestrator())
    client = TestClient(api_module.app)
    client.post(
        "/chat/stream",
        json={
            "prompt": "query",
            "auth_mode": "hosted",
            "user_id": "hosted-user",
            "fabric_user_token": "tok-xyz",
        },
    )

    assert captured.get("fabric_user_token") == "tok-xyz"
    assert captured.get("auth_mode") == "hosted"
    assert captured.get("user_id") == "hosted-user"
    assert captured.get("channel") == "api"


def test_streaming_endpoint_default_values_for_optional_fields(monkeypatch):
    """Integration: ChatRequest uses default user_id and auth_mode when omitted."""
    captured: dict = {}

    class CapturingOrchestrator:
        async def stream(self, **kwargs) -> AsyncIterator[str]:
            captured.update(kwargs)
            yield "ok"

    monkeypatch.setattr(api_module, "get_orchestrator", lambda: CapturingOrchestrator())
    client = TestClient(api_module.app)
    client.post("/chat/stream", json={"prompt": "minimal request"})

    assert captured.get("user_id") == "local-user"
    assert captured.get("auth_mode") == "local"
    assert captured.get("fabric_user_token") is None


def test_streaming_endpoint_returns_422_when_prompt_is_missing(monkeypatch):
    """Integration: ChatRequest rejects requests that omit the required `prompt` field."""

    class FakeOrchestrator2:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "never"

    monkeypatch.setattr(api_module, "get_orchestrator", lambda: FakeOrchestrator2())
    client = TestClient(api_module.app)
    response = client.post("/chat/stream", json={"user_id": "u1"})
    assert response.status_code == 422


def test_streaming_endpoint_sse_format_includes_data_prefix(monkeypatch):
    """Integration: each yielded chunk is formatted as an SSE data line."""

    class SseOrchestrator:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "test chunk"

    monkeypatch.setattr(api_module, "get_orchestrator", lambda: SseOrchestrator())
    client = TestClient(api_module.app)
    response = client.post("/chat/stream", json={"prompt": "p"})

    assert "data: test chunk" in response.text
    assert "event: done" in response.text

