from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest
from langgraph_fabric_console.console import run_console


class FakeStatus:
    def __init__(self) -> None:
        self.stop_calls = 0
        self.start_calls = 0
        self.update_calls: list[str] = []

    def __enter__(self) -> "FakeStatus":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    def stop(self) -> None:
        self.stop_calls += 1

    def start(self) -> None:
        self.start_calls += 1

    def update(self, text: str) -> None:
        self.update_calls.append(text)


class FakeConsole:
    def __init__(self, user_inputs: Iterator[str]) -> None:
        self._inputs = user_inputs
        self.print_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.status_contexts: list[FakeStatus] = []

    def input(self, _: str) -> str:
        return next(self._inputs)

    def print(self, *args: Any, **kwargs: Any) -> None:
        self.print_calls.append((args, kwargs))

    def status(self, _text: str, spinner: str) -> FakeStatus:
        assert spinner == "dots"
        context = FakeStatus()
        self.status_contexts.append(context)
        return context


@pytest.mark.asyncio
async def test_run_console_streams_response_and_updates_history() -> None:
    class FakeOrchestrator:
        def __init__(self) -> None:
            self.stream_calls: list[dict[str, Any]] = []

        async def stream(self, **kwargs):
            self.stream_calls.append({**kwargs, "history_snapshot": list(kwargs["history"])})
            yield "Hello"
            yield " world"

    orchestrator = FakeOrchestrator()
    fake_console = FakeConsole(iter(["what is revenue?", "show me margin", ""]))

    with patch("langgraph_fabric_console.console.console", fake_console):
        await run_console(orchestrator)

    assert len(orchestrator.stream_calls) == 2
    assert orchestrator.stream_calls[0]["prompt"] == "what is revenue?"
    assert orchestrator.stream_calls[0]["channel"] == "console"
    assert orchestrator.stream_calls[0]["auth_mode"] == "local"
    assert orchestrator.stream_calls[0]["user_id"] == "console-user"
    assert len(orchestrator.stream_calls[0]["history_snapshot"]) == 0
    assert len(orchestrator.stream_calls[1]["history_snapshot"]) == 2


@pytest.mark.asyncio
async def test_run_console_exits_on_empty_input() -> None:
    class FakeOrchestrator:
        stream_called = False

        async def stream(self, **_kwargs):
            self.stream_called = True
            yield "should not be reached"

    orchestrator = FakeOrchestrator()
    fake_console = FakeConsole(iter(["   "]))

    with patch("langgraph_fabric_console.console.console", fake_console):
        await run_console(orchestrator)

    assert not orchestrator.stream_called


@pytest.mark.asyncio
async def test_run_console_handles_tool_message_chunks() -> None:
    class FakeOrchestrator:
        async def stream(self, **_kwargs):
            yield "\n[tool] querying Fabric"
            yield "Done"

    orchestrator = FakeOrchestrator()
    fake_console = FakeConsole(iter(["run tool", ""]))

    with patch("langgraph_fabric_console.console.console", fake_console):
        await run_console(orchestrator)

    status = fake_console.status_contexts[0]
    assert status.stop_calls == 1
    assert status.start_calls == 1
    assert status.update_calls
    assert any(
        args and args[0] == "[tool] querying Fabric" and kwargs.get("style") == "dim yellow"
        for args, kwargs in fake_console.print_calls
    )
