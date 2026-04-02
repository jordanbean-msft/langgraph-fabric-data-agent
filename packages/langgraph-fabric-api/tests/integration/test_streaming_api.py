import importlib
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

api_module = importlib.import_module("langgraph_fabric_api.app")


class FakeOrchestrator:
    async def stream(self, **_kwargs) -> AsyncIterator[str]:
        yield "chunk-1"
        yield "chunk-2"


async def _fake_obo(_bearer_token: str, _settings, scope: str) -> str:
    assert scope == "https://api.fabric.microsoft.com/.default"
    return "fake-fabric-token"


def _get_fake_orchestrator() -> FakeOrchestrator:
    return FakeOrchestrator()


def test_streaming_endpoint(monkeypatch, fake_settings):
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", _get_fake_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", _fake_obo)
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
    monkeypatch.setattr(api_module, "get_orchestrator", _get_fake_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", _fake_obo)
    client = TestClient(api_module.app, raise_server_exceptions=False)
    response = client.post("/chat/stream", json={"prompt": "hello"})
    assert response.status_code == 401


def test_streaming_endpoint_chat_only_mode_still_requires_auth(monkeypatch, fake_settings):
    fake_settings.mcp_servers = []
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", _get_fake_orchestrator)
    client = TestClient(api_module.app, raise_server_exceptions=False)
    response = client.post("/chat/stream", json={"prompt": "hello"})
    assert response.status_code == 401


def test_streaming_endpoint_obo_token_reaches_orchestrator(monkeypatch, fake_settings):
    """Integration: scope-specific OBO tokens reach orchestrator.stream()."""
    captured: dict = {}

    class CapturingOrchestrator:
        async def stream(self, **kwargs) -> AsyncIterator[str]:
            captured.update(kwargs)
            yield "response"

    async def capturing_obo(_bearer_token: str, _settings, scope: str) -> str:
        assert scope == "https://api.fabric.microsoft.com/.default"
        return "obo-fabric-token"

    def get_capturing_orchestrator() -> CapturingOrchestrator:
        return CapturingOrchestrator()

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", get_capturing_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", capturing_obo)
    client = TestClient(api_module.app)
    client.post(
        "/chat/stream",
        json={"prompt": "query"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )

    assert captured.get("mcp_user_tokens") == {"fabric": "obo-fabric-token"}
    assert captured.get("auth_mode") == "api"
    assert captured.get("channel") == "api"


def test_streaming_endpoint_returns_422_when_prompt_is_missing(monkeypatch, fake_settings):
    """Integration: ChatRequest rejects requests that omit the required `prompt` field."""
    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", _get_fake_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", _fake_obo)
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

    def get_sse_orchestrator() -> SseOrchestrator:
        return SseOrchestrator()

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", get_sse_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", _fake_obo)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "p"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )

    assert "data: test chunk" in response.text
    assert "event: done" in response.text


def test_streaming_endpoint_multiline_chunk_is_valid_sse(monkeypatch, fake_settings):
    """Integration: multiline chunks are emitted as repeated `data:` lines."""

    class MultilineOrchestrator:
        async def stream(self, **_kwargs) -> AsyncIterator[str]:
            yield "line-1\nline-2"

    def get_multiline_orchestrator() -> MultilineOrchestrator:
        return MultilineOrchestrator()

    monkeypatch.setattr(api_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(api_module, "get_orchestrator", get_multiline_orchestrator)
    monkeypatch.setattr(api_module, "_get_token_obo", _fake_obo)
    client = TestClient(api_module.app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "p"},
        headers={"Authorization": "Bearer fake-caller-token"},
    )

    assert response.status_code == 200
    assert "event: text\ndata: line-1\ndata: line-2\n" in response.text
