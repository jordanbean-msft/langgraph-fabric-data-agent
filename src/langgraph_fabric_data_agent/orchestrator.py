"""Shared orchestrator for API, console, and hosted surfaces."""

import logging
import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage

from langgraph_fabric_data_agent.graph import build_graph
from langgraph_fabric_data_agent.logging_setup import set_log_context
from langgraph_fabric_data_agent.tools import build_fabric_tool

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinate graph execution and streaming."""

    def __init__(self, chat_model, fabric_client):
        fabric_tool = build_fabric_tool(fabric_client)
        self._graph = build_graph(chat_model, fabric_tool)

    async def run(
        self,
        *,
        prompt: str,
        channel: str,
        auth_mode: str,
        user_id: str,
        fabric_user_token: str | None = None,
    ) -> str:
        """Execute one complete run and return final text."""
        invocation_id = str(uuid.uuid4())[:8]
        set_log_context(invocation_id=invocation_id, channel=channel, mode=auth_mode, user_id=user_id)

        state = {
            "messages": [HumanMessage(content=prompt)],
            "auth_mode": auth_mode,
            "user_id": user_id,
            "fabric_user_token": fabric_user_token,
        }
        logger.info("Starting non-streaming run")
        result = await self._graph.ainvoke(state)
        return str(result["messages"][-1].content)

    async def stream(
        self,
        *,
        prompt: str,
        channel: str,
        auth_mode: str,
        user_id: str,
        fabric_user_token: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield streaming updates from graph execution."""
        invocation_id = str(uuid.uuid4())[:8]
        set_log_context(invocation_id=invocation_id, channel=channel, mode=auth_mode, user_id=user_id)

        state = {
            "messages": [HumanMessage(content=prompt)],
            "auth_mode": auth_mode,
            "user_id": user_id,
            "fabric_user_token": fabric_user_token,
        }

        async for event in self._graph.astream_events(state, version="v2"):
            event_name = event.get("event", "")
            if event_name == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and getattr(chunk, "content", ""):
                    yield str(chunk.content)
            elif event_name == "on_tool_start":
                yield "\n[tool] Querying Fabric Data Agent...\n"
            elif event_name == "on_tool_end":
                yield "\n[tool] Fabric Data Agent response received.\n"
