"""Console interaction surface."""

import asyncio

from langgraph_fabric_data_agent.orchestrator import AgentOrchestrator


async def run_console(orchestrator: AgentOrchestrator) -> None:
    """Run interactive terminal chat with streamed responses."""
    print("LangGraph Fabric MCP console. Press Enter on empty input to exit.")
    while True:
        prompt = await asyncio.to_thread(input, "You: ")
        if not prompt.strip():
            break

        print("Assistant: ", end="", flush=True)
        async for chunk in orchestrator.stream(
            prompt=prompt,
            channel="console",
            auth_mode="local",
            user_id="console-user",
        ):
            print(chunk, end="", flush=True)
        print()
