from collections.abc import AsyncIterator
import importlib

from fastapi.testclient import TestClient

api_module = importlib.import_module("langgraph_fabric_data_agent.api.app")


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
