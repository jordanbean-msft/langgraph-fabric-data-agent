"""Unit tests for the LangGraph workflow definition (graph/workflow.py)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langgraph_fabric_core.graph.workflow import build_graph


def _make_chat_model(
    *,
    bound_response: AIMessage | None = None,
    direct_response: str = "Direct answer",
    finalize_response: str = "Synthesized answer",
):
    """Build a mock chat model pair (bound_llm, base_llm) for workflow tests."""
    if bound_response is None:
        bound_response = AIMessage(content=direct_response)

    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=bound_response)

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_bound
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=finalize_response))

    return mock_llm, mock_bound


def _make_tool_call_message(
    tool_name: str = "mcp_fabric",
    query: str = "test query",
) -> AIMessage:
    """Build an AIMessage that triggers a tool call."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": {"query": query},
                "id": "call-test-1",
                "type": "tool_call",
            }
        ],
    )


def _make_simple_tool(
    name: str = "mcp_fabric",
    response: str = "tool result",
) -> StructuredTool:
    """Create a simple tool without InjectedState for workflow tests."""

    async def fn(query: str) -> str:
        return response

    return StructuredTool.from_function(
        coroutine=fn,
        name=name,
        description="test tool",
    )


def _make_state(**overrides) -> dict:
    base = {
        "messages": [HumanMessage(content="test prompt")],
        "auth_mode": "local",
        "user_id": "test-user",
        "mcp_user_tokens": {},
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_build_graph_returns_direct_answer_when_no_tool_calls() -> None:
    """Graph routes to END when LLM answers without making tool calls."""
    mock_llm, mock_bound = _make_chat_model(direct_response="Here is the direct answer")
    graph = build_graph(mock_llm, [_make_simple_tool()])

    result = await graph.ainvoke(_make_state())

    assert result["messages"][-1].content == "Here is the direct answer"
    mock_bound.ainvoke.assert_awaited_once()
    mock_llm.ainvoke.assert_not_awaited()  # finalize not reached in this path


@pytest.mark.asyncio
async def test_build_graph_routes_through_tools_and_finalize_when_tool_called() -> None:
    """Graph routes through tools node and finalize when LLM makes tool calls."""
    tool_call_msg = _make_tool_call_message(query="top 5 customers")
    mock_llm, mock_bound = _make_chat_model(
        bound_response=tool_call_msg,
        finalize_response="Synthesized: top 5 customers are ...",
    )

    graph = build_graph(mock_llm, [_make_simple_tool(response="Customer A, B, C")])

    result = await graph.ainvoke(_make_state(messages=[HumanMessage(content="top 5 customers")]))

    assert "Synthesized" in result["messages"][-1].content
    mock_bound.ainvoke.assert_awaited_once()
    mock_llm.ainvoke.assert_awaited_once()  # finalize invoked


@pytest.mark.asyncio
async def test_build_graph_finalize_includes_tool_output_in_synthesized_prompt() -> None:
    """Finalize node injects tool output into the prompt sent to the LLM."""
    mock_llm, _ = _make_chat_model(
        bound_response=_make_tool_call_message(),
        finalize_response="done",
    )

    graph = build_graph(mock_llm, [_make_simple_tool(response="TOOL_OUTPUT_12345")])

    await graph.ainvoke(_make_state())

    finalize_call_args = mock_llm.ainvoke.await_args
    messages_to_finalize = finalize_call_args.args[0]
    assert len(messages_to_finalize) == 1
    assert "TOOL_OUTPUT_12345" in messages_to_finalize[0].content


@pytest.mark.asyncio
async def test_build_graph_finalize_creates_synthesized_prompt_for_llm() -> None:
    """Finalize node builds a synthesized prompt and passes it to the LLM."""
    mock_llm, _ = _make_chat_model(
        bound_response=_make_tool_call_message(),
        finalize_response="done",
    )

    graph = build_graph(mock_llm, [_make_simple_tool(response="TOOL_OUTPUT_12345")])

    await graph.ainvoke(_make_state())

    # Verify finalize called the LLM with a single synthesized HumanMessage
    finalize_call_args = mock_llm.ainvoke.await_args
    messages_to_finalize = finalize_call_args.args[0]
    assert len(messages_to_finalize) == 1
    assert "TOOL_OUTPUT_12345" in messages_to_finalize[0].content
    assert "analytics assistant" in messages_to_finalize[0].content


@pytest.mark.asyncio
async def test_build_graph_finalize_includes_user_prompt_in_synthesized_prompt() -> None:
    """Finalize node preserves the original user request in the synthesized prompt.

    Regression test: AgentState.messages must use add_messages so the HumanMessage
    is not discarded when subsequent nodes update the messages field.
    """
    mock_llm, _ = _make_chat_model(
        bound_response=_make_tool_call_message(),
        finalize_response="done",
    )

    graph = build_graph(mock_llm, [_make_simple_tool(response="some result")])

    await graph.ainvoke(_make_state(messages=[HumanMessage(content="ORIGINAL_USER_QUERY_XYZ")]))

    finalize_call_args = mock_llm.ainvoke.await_args
    messages_to_finalize = finalize_call_args.args[0]
    assert len(messages_to_finalize) == 1
    assert "ORIGINAL_USER_QUERY_XYZ" in messages_to_finalize[0].content


@pytest.mark.asyncio
async def test_build_graph_binds_tool_to_llm() -> None:
    """build_graph calls bind_tools to equip the LLM with MCP tools."""
    mock_llm, _ = _make_chat_model()
    mcp_tool = _make_simple_tool()

    build_graph(mock_llm, [mcp_tool])

    mock_llm.bind_tools.assert_called_once_with([mcp_tool])


@pytest.mark.asyncio
async def test_build_graph_passes_auth_state_through_messages() -> None:
    """Auth state fields are preserved in the graph's final state."""
    mock_llm, _ = _make_chat_model(direct_response="ok")
    graph = build_graph(mock_llm, [_make_simple_tool()])

    state = _make_state(
        auth_mode="m365", user_id="m365-user-123", mcp_user_tokens={"fabric": "tok-abc"}
    )
    result = await graph.ainvoke(state)

    assert result["auth_mode"] == "m365"
    assert result["user_id"] == "m365-user-123"
    assert result["mcp_user_tokens"] == {"fabric": "tok-abc"}


@pytest.mark.asyncio
async def test_build_graph_without_tools_uses_chat_model_directly() -> None:
    """Graph supports chat-only mode when no MCP tools are configured."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Chat-only answer"))

    graph = build_graph(mock_llm, [])

    result = await graph.ainvoke(_make_state())

    assert result["messages"][-1].content == "Chat-only answer"
    mock_llm.ainvoke.assert_awaited_once()
    mock_llm.bind_tools.assert_not_called()
