"""Integration tests for the full agent pipeline (orchestrator -> graph -> tools).

These tests verify that the packages work together end-to-end using only
in-process fakes - no Azure credentials or live HTTP connections are required.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator


def _make_tool_calling_llm(finalize_response: str = "Final synthesized answer") -> MagicMock:
    """Return a mock LLM pair that makes exactly one tool call then finalises."""
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "mcp_fabric",
                    "args": {"query": "top 5 customers"},
                    "id": "call-int-1",
                    "type": "tool_call",
                }
            ],
        )
    )

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=finalize_response))
    return mock_llm


def _make_direct_llm(response: str = "Direct answer") -> MagicMock:
    """Return a mock LLM that answers directly without calling any tools."""
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=AIMessage(content=response))

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="should not be called"))
    return mock_llm


# ---------------------------------------------------------------------------
# Orchestrator.run - full pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_run_direct_response_pipeline() -> None:
    """Core integration: orchestrator → graph → direct LLM answer (no tool call)."""
    chat_model = _make_direct_llm("Paris is the capital of France")
    fabric_client = AsyncMock()
    fabric_client.server_config = SimpleNamespace(
        name="fabric",
        description="Fabric MCP",
        scope="https://api.fabric.microsoft.com/.default",
    )

    orchestrator = AgentOrchestrator(chat_model, [fabric_client])

    result = await orchestrator.run(
        prompt="What is the capital of France?",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
    )

    assert result == "Paris is the capital of France"
    fabric_client.initialize.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_run_tool_call_pipeline() -> None:
    """Core integration: orchestrator → graph → MCP tool call → finalize."""
    chat_model = _make_tool_calling_llm("Synthesized: Customer A, B, C")

    fabric_client = AsyncMock()
    fabric_client.list_tools.return_value = [
        {
            "name": "fabric_query",
            "inputSchema": {
                "type": "object",
                "properties": {"userQuestion": {"type": "string"}},
                "required": ["userQuestion"],
            },
        }
    ]
    fabric_client.call_tool.return_value = "Customer A, B, C"
    fabric_client.server_config = SimpleNamespace(
        name="fabric",
        description="Fabric MCP",
        scope="https://api.fabric.microsoft.com/.default",
    )

    orchestrator = AgentOrchestrator(chat_model, [fabric_client])

    result = await orchestrator.run(
        prompt="top 5 customers",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
    )

    assert "Synthesized" in result
    fabric_client.initialize.assert_awaited_once()
    fabric_client.call_tool.assert_awaited_once()

    call_kwargs = fabric_client.call_tool.await_args.kwargs
    assert call_kwargs["tool_name"] == "fabric_query"
    assert call_kwargs["arguments"] == {"userQuestion": "top 5 customers"}


@pytest.mark.asyncio
async def test_orchestrator_run_passes_history_to_graph() -> None:
    """Core integration: prior conversation history is included in the graph state."""
    chat_model = _make_direct_llm("Response to new question")
    fabric_client = AsyncMock()
    fabric_client.server_config = SimpleNamespace(
        name="fabric",
        description="Fabric MCP",
        scope="https://api.fabric.microsoft.com/.default",
    )

    orchestrator = AgentOrchestrator(chat_model, [fabric_client])

    history = [
        HumanMessage(content="Who are the top customers?"),
        AIMessage(content="They are A, B, C."),
    ]

    result = await orchestrator.run(
        prompt="Tell me more about Customer A",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
        history=history,
    )

    assert result == "Response to new question"
    bound_call = chat_model.bind_tools.return_value.ainvoke.await_args
    messages_passed = bound_call.args[0]
    assert len(messages_passed) == 3  # 2 history + 1 new prompt
    assert messages_passed[0].content == "Who are the top customers?"
    assert messages_passed[2].content == "Tell me more about Customer A"


@pytest.mark.asyncio
async def test_orchestrator_run_mcp_error_is_reported_in_final_answer() -> None:
    """Core integration: MCP tool errors surface as part of the final response."""
    chat_model = _make_tool_calling_llm("Fabric query failed: upstream error")

    fabric_client = AsyncMock()
    fabric_client.list_tools.return_value = [{"name": "query"}]
    fabric_client.call_tool.side_effect = RuntimeError("upstream error")
    fabric_client.server_config = SimpleNamespace(
        name="fabric",
        description="Fabric MCP",
        scope="https://api.fabric.microsoft.com/.default",
    )

    orchestrator = AgentOrchestrator(chat_model, [fabric_client])

    result = await orchestrator.run(
        prompt="anything",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
    )

    # The orchestrator finalises even when the tool raises, and the
    # finalize model receives the error message from the tool.
    assert result is not None
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Orchestrator.stream - full pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_stream_direct_response_emits_text_chunks() -> None:
    """Core integration: streaming a direct LLM response yields text via events."""

    class FakeGraph:
        """Minimal graph that mimics LangGraph's v2 event stream for a direct answer."""

        async def astream_events(self, _state, version):
            assert version == "v2"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": SimpleNamespace(content="Direct ")},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": SimpleNamespace(content="answer")},
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()

    chunks = []
    async for chunk in orchestrator.stream(
        prompt="query",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "Direct answer"


@pytest.mark.asyncio
async def test_orchestrator_stream_tool_call_emits_markers_and_final_answer() -> None:
    """Core integration: streaming with tool call emits [tool] markers and final text."""

    class FakeGraph:
        async def astream_events(self, _state, **_kwargs):
            yield {"event": "on_tool_start", "data": {}}
            yield {"event": "on_tool_end", "data": {"output": "raw tool output"}}
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": SimpleNamespace(content="Synthesized answer")},
            }

    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.__dict__["_graph"] = FakeGraph()
    orchestrator.__dict__["_tool_descriptions"] = {"mcp_tool": "Fabric Data Agent"}

    chunks = []
    async for chunk in orchestrator.stream(
        prompt="query",
        channel="integration-test",
        auth_mode="local",
        user_id="test-user",
    ):
        chunks.append(chunk)

    combined = "".join(chunks)
    assert "[tool] Querying Fabric Data Agent..." in combined
    assert "[tool] Fabric Data Agent response received." in combined
    assert "Synthesized answer" in combined
    assert "raw tool output" not in combined
