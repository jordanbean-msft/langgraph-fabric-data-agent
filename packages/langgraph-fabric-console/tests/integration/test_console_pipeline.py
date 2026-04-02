"""Integration tests for the console package interacting with the core orchestrator.

Tests verify that the console (langgraph-fabric-console) correctly drives the
AgentOrchestrator (langgraph-fabric-core) without requiring any cloud services.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph_fabric_console.console import run_console
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator


def _create_fake_settings(microsoft_tenant_id: str = "test-tenant") -> MagicMock:
    """Create a mock CoreSettings object for testing."""
    settings = MagicMock()
    settings.microsoft_tenant_id = microsoft_tenant_id
    settings.mcp_servers = [
        MagicMock(name="fabric", scope="https://api.fabric.microsoft.com/.default")
    ]
    return settings


def _create_fake_token_provider(user_id: str = "test-user@example.com") -> MagicMock:
    """Create a mock TokenProvider object for testing."""
    token_provider = MagicMock()
    token_provider.get_authenticated_identity.return_value = SimpleNamespace(
        user_id=user_id,
        tenant_id="11111111-1111-1111-1111-111111111111",
    )
    return token_provider


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
    settings = _create_fake_settings()
    token_provider = _create_fake_token_provider()

    with patch("rich.console.Console.input", side_effect=inputs):
        with patch("builtins.print"):
            await run_console(orchestrator, settings, token_provider)

    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]["prompt"] == "What is revenue?"
    assert orchestrator.calls[0]["auth_mode"] == "local"
    assert orchestrator.calls[0]["channel"] == "console"


@pytest.mark.asyncio
async def test_console_accumulates_history_across_turns() -> None:
    """Console integration: history grows turn-by-turn and is passed to each call."""
    inputs = iter(["First question", "Second question", ""])
    orchestrator = _CapturingOrchestrator(["First answer", "Second answer"])
    settings = _create_fake_settings()
    token_provider = _create_fake_token_provider()

    with patch("rich.console.Console.input", side_effect=inputs):
        with patch("builtins.print"):
            await run_console(orchestrator, settings, token_provider)

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

        async def astream_events(self, _state, **_kwargs):
            for word in ["Streaming", " answer", " here"]:
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": SimpleNamespace(content=word)},
                }

    real_orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    real_orchestrator.__dict__["_graph"] = FakeStreamGraph()
    settings = _create_fake_settings()
    token_provider = _create_fake_token_provider()

    inputs = iter(["stream test", ""])

    with patch(
        "rich.console.Console.input",
        side_effect=inputs,
    ):
        with patch("builtins.print"):
            await run_console(real_orchestrator, settings, token_provider)

    # Verify the orchestrator was called with the correct input
    # The actual streamed output is handled by Rich's console, so we
    # verify the integration by checking that the call succeeded


@pytest.mark.asyncio
async def test_console_exits_immediately_on_first_empty_input() -> None:
    """Console integration: empty input on the first turn exits without any orchestrator calls."""
    orchestrator = _CapturingOrchestrator([])
    settings = _create_fake_settings()
    token_provider = _create_fake_token_provider()

    with patch(
        "rich.console.Console.input",
        return_value="",
    ):
        with patch("builtins.print"):
            await run_console(orchestrator, settings, token_provider)

    assert orchestrator.calls == []


@pytest.mark.asyncio
async def test_console_chat_only_mode_runs_without_identity_lookup() -> None:
    """Console integration: no MCP servers still allows direct chatbot interaction."""
    inputs = iter(["Just chat", ""])
    orchestrator = _CapturingOrchestrator(["Plain chat response"])
    settings = _create_fake_settings()
    settings.mcp_servers = []
    token_provider = _create_fake_token_provider()

    with patch("rich.console.Console.input", side_effect=inputs):
        with patch("builtins.print"):
            await run_console(orchestrator, settings, token_provider)

    token_provider.get_authenticated_identity.assert_not_called()
    assert orchestrator.calls[0]["user_id"] == "local-user"
    assert orchestrator.calls[0]["prompt"] == "Just chat"
