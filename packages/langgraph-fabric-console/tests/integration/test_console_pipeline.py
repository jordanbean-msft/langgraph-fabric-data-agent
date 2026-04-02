"""Integration tests for the console package interacting with the core orchestrator.

Tests verify that the console (langgraph-fabric-console) correctly drives the
AgentOrchestrator (langgraph-fabric-core) without requiring any cloud services.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph_fabric_console.console import run_console
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator


class _CapturingOrchestrator:
    """Captures calls to stream() with snapshot copies of kwargs."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls: list[dict] = []

    async def stream(self, **kwargs):
        # Snapshot history so later mutations don't affect recorded values
        self.calls.append({**kwargs, "history": list(kwargs.get("history", []))})
        response = next(self._responses, "default")
        for char in response:
            yield char


@pytest.mark.asyncio
async def test_console_sends_prompt_to_orchestrator() -> None:
    """Console integration: user input reaches orchestrator.stream() as `prompt`."""
    inputs = iter(["What is revenue?", ""])
    orchestrator = _CapturingOrchestrator(["Revenue is $100M."])

    with patch("langgraph_fabric_console.console.asyncio.to_thread", new=AsyncMock(side_effect=inputs)):
        with patch("builtins.print"):
            await run_console(orchestrator)

    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]["prompt"] == "What is revenue?"
    assert orchestrator.calls[0]["auth_mode"] == "local"
    assert orchestrator.calls[0]["channel"] == "console"


@pytest.mark.asyncio
async def test_console_accumulates_history_across_turns() -> None:
    """Console integration: history grows turn-by-turn and is passed to each call."""
    inputs = iter(["First question", "Second question", ""])
    orchestrator = _CapturingOrchestrator(["First answer", "Second answer"])

    with patch("langgraph_fabric_console.console.asyncio.to_thread", new=AsyncMock(side_effect=inputs)):
        with patch("builtins.print"):
            await run_console(orchestrator)

    assert len(orchestrator.calls) == 2

    # First turn: no history yet
    assert orchestrator.calls[0]["history"] == []

    # Second turn: history has the first exchange
    history_turn_2 = orchestrator.calls[1]["history"]
    assert len(history_turn_2) == 2
    assert isinstance(history_turn_2[0], HumanMessage)
    assert history_turn_2[0].content == "First question"
    assert isinstance(history_turn_2[1], AIMessage)
    assert history_turn_2[1].content == "First answer"


@pytest.mark.asyncio
async def test_console_with_real_orchestrator_streaming() -> None:
    """Console integration: streaming tokens from graph are printed to the terminal."""

    class FakeStreamGraph:
        """Graph that yields streaming events like LangGraph does."""

        async def astream_events(self, _state, version):
            for word in ["Streaming", " answer", " here"]:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": SimpleNamespace(content=word)},
                }

    real_orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    real_orchestrator.__dict__["_graph"] = FakeStreamGraph()

    inputs = iter(["stream test", ""])
    printed_output: list[str] = []

    def capture_print(*args, **kwargs):
        printed_output.append("".join(str(a) for a in args))

    with patch(
        "langgraph_fabric_console.console.asyncio.to_thread",
        new=AsyncMock(side_effect=inputs),
    ):
        with patch("builtins.print", side_effect=capture_print):
            await run_console(real_orchestrator)

    combined = "".join(printed_output)
    assert "Streaming" in combined
    assert "answer" in combined


@pytest.mark.asyncio
async def test_console_exits_immediately_on_first_empty_input() -> None:
    """Console integration: empty input on the first turn exits without any orchestrator calls."""
    orchestrator = _CapturingOrchestrator([])

    with patch(
        "langgraph_fabric_console.console.asyncio.to_thread",
        new=AsyncMock(return_value=""),
    ):
        with patch("builtins.print"):
            await run_console(orchestrator)

    assert orchestrator.calls == []

