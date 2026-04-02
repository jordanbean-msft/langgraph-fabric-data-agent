from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph_fabric_core.graph.orchestrator import (
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


def test_stringify_stream_chunk_content_converts_non_string_non_list_to_str() -> None:
    assert _stringify_stream_chunk_content(42) == "42"
    assert _stringify_stream_chunk_content(None) == "None"


@pytest.mark.asyncio
async def test_run_returns_final_text_from_graph() -> None:
    """run() invokes the graph and returns the last message content as text."""

    class FakeGraph:
        async def ainvoke(self, state):
            assert "messages" in state
            return {
                "messages": [
                    state["messages"][0],
                    SimpleNamespace(content="Final answer text"),
                ]
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    result = await orchestrator.run(
        prompt="What is 2+2?",
        channel="test",
        auth_mode="local",
        user_id="test-user",
    )

    assert result == "Final answer text"


@pytest.mark.asyncio
async def test_run_prepends_history_messages_to_state() -> None:
    """run() includes prior history messages before the new prompt."""
    captured: dict = {}

    class FakeGraph:
        async def ainvoke(self, state):
            captured["state"] = state
            return {"messages": state["messages"] + [SimpleNamespace(content="ok")]}

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    history = [HumanMessage(content="prev"), AIMessage(content="prev response")]
    await orchestrator.run(
        prompt="new question",
        channel="test",
        auth_mode="local",
        user_id="test-user",
        history=history,
    )

    messages = captured["state"]["messages"]
    assert len(messages) == 3  # 2 history + 1 new
    assert messages[0].content == "prev"
    assert messages[1].content == "prev response"
    assert messages[2].content == "new question"


@pytest.mark.asyncio
async def test_run_passes_auth_fields_to_graph_state() -> None:
    """run() passes auth_mode, user_id, and fabric_user_token into graph state."""
    captured: dict = {}

    class FakeGraph:
        async def ainvoke(self, state):
            captured["state"] = state
            return {"messages": state["messages"] + [SimpleNamespace(content="ok")]}

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    await orchestrator.run(
        prompt="query",
        channel="hosted",
        auth_mode="hosted",
        user_id="hosted-user",
        fabric_user_token="tok-abc",
    )

    state = captured["state"]
    assert state["auth_mode"] == "hosted"
    assert state["user_id"] == "hosted-user"
    assert state["fabric_user_token"] == "tok-abc"


@pytest.mark.asyncio
async def test_run_handles_list_content_from_graph() -> None:
    """run() stringifies response block lists returned by some model variants."""

    class FakeGraph:
        async def ainvoke(self, state):
            return {
                "messages": [
                    SimpleNamespace(
                        content=[
                            {"type": "text", "text": "Block one"},
                            {"type": "text", "text": " block two"},
                        ]
                    )
                ]
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    result = await orchestrator.run(
        prompt="query",
        channel="api",
        auth_mode="local",
        user_id="u1",
    )

    assert result == "Block one block two"


@pytest.mark.asyncio
async def test_stream_skips_chunks_with_empty_content() -> None:
    """Streaming suppresses chunks where stringified content is empty."""

    class FakeGraph:
        async def astream_events(self, _state, version):
            yield {"event": "on_chat_model_stream", "data": {"chunk": SimpleNamespace(content="")}}
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": SimpleNamespace(content="real content")},
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    chunks = []
    async for chunk in orchestrator.stream(
        prompt="p",
        channel="c",
        auth_mode="local",
        user_id="u",
    ):
        chunks.append(chunk)

    assert chunks == ["real content"]
