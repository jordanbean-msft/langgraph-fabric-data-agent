"""Console interaction surface."""

import asyncio

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from langgraph_fabric_data_agent.graph.orchestrator import AgentOrchestrator


async def run_console(orchestrator: AgentOrchestrator) -> None:
    """Run interactive terminal chat with streamed responses."""
    print("LangGraph Fabric MCP console. Press Enter on empty input to exit.")
    history: list[BaseMessage] = []
    while True:
        prompt = await asyncio.to_thread(input, "You: ")
        if not prompt.strip():
            break

        print("Assistant: ", end="", flush=True)
        chunks: list[str] = []
        async for chunk in orchestrator.stream(
            prompt=prompt,
            channel="console",
            auth_mode="local",
            user_id="console-user",
            history=history,
        ):
            print(chunk, end="", flush=True)
            chunks.append(chunk)
        print()

        history.append(HumanMessage(content=prompt))
        history.append(AIMessage(content="".join(chunks)))
