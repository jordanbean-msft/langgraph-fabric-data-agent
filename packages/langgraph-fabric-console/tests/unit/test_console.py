from unittest.mock import patch

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

    with patch("rich.console.Console.input", side_effect=inputs):
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

    with patch("rich.console.Console.input", return_value=""):
        with patch("builtins.print"):
            await run_console(orchestrator)

    assert not orchestrator.stream_called
