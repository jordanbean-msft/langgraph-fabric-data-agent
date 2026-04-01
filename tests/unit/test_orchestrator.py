from types import SimpleNamespace

import pytest

from langgraph_fabric_data_agent.graph.orchestrator import (
    AgentOrchestrator,
    _stringify_stream_chunk_content,
)


def test_stringify_stream_chunk_content_returns_plain_strings() -> None:
    assert _stringify_stream_chunk_content("hello") == "hello"


def test_stringify_stream_chunk_content_flattens_response_blocks() -> None:
    content = [
        {"type": "text", "text": "Hello"},
        {"type": "text", "text": " world"},
        {"id": "msg_123", "index": 0},
    ]

    assert _stringify_stream_chunk_content(content) == "Hello world"


def test_stringify_stream_chunk_content_ignores_non_text_blocks() -> None:
    content = [
        {"type": "reasoning", "summary": []},
        {"id": "msg_123", "index": 0},
    ]

    assert _stringify_stream_chunk_content(content) == ""


@pytest.mark.asyncio
async def test_stream_does_not_emit_raw_tool_output_on_tool_end() -> None:
    class FakeGraph:
        async def astream_events(self, _state, version):
            assert version == "v2"
            yield {"event": "on_tool_start", "data": {}}
            yield {
                "event": "on_tool_end",
                "data": {"output": "RAW_TOOL_OUTPUT_SHOULD_NOT_BE_EMITTED"},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": SimpleNamespace(content="Final synthesized answer")},
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    chunks: list[str] = []
    async for chunk in orchestrator.stream(
        prompt="top 5 customers",
        channel="console",
        auth_mode="local",
        user_id="console-user",
    ):
        chunks.append(chunk)

    combined_output = "".join(chunks)
    assert "RAW_TOOL_OUTPUT_SHOULD_NOT_BE_EMITTED" not in combined_output
    assert "[tool] Querying Fabric Data Agent..." in combined_output
    assert "[tool] Fabric Data Agent response received." in combined_output
    assert "Final synthesized answer" in combined_output
