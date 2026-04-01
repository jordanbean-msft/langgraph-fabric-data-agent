from unittest.mock import AsyncMock, patch

import pytest
from langgraph_fabric_console.console import run_console


@pytest.mark.asyncio
async def test_run_console_streams_response_and_updates_history() -> None:
    class FakeOrchestrator:
        async def stream(self, **kwargs):
            yield "Hello"
            yield " world"

    orchestrator = FakeOrchestrator()
    inputs = iter(["what is revenue?", ""])

    with patch("langgraph_fabric_console.console.asyncio.to_thread", new=AsyncMock(side_effect=inputs)):
        with patch("builtins.print"):
            await run_console(orchestrator)


@pytest.mark.asyncio
async def test_run_console_exits_on_empty_input() -> None:
    class FakeOrchestrator:
        stream_called = False

        async def stream(self, **kwargs):
            self.stream_called = True
            yield "should not be reached"

    orchestrator = FakeOrchestrator()

    with patch("langgraph_fabric_console.console.asyncio.to_thread", new=AsyncMock(return_value="")):
        with patch("builtins.print"):
            await run_console(orchestrator)

    assert not orchestrator.stream_called
