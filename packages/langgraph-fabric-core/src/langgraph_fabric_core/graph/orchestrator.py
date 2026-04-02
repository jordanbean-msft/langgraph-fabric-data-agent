"""Shared orchestrator for all client surfaces."""

import logging
import uuid
from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage

from langgraph_fabric_core.core.logging import set_log_context
from langgraph_fabric_core.graph.workflow import build_graph
from langgraph_fabric_core.mcp.tools import build_mcp_tool

logger = logging.getLogger(__name__)


def _stringify_stream_chunk_content(content: object) -> str:
    """Convert LangChain stream chunk payloads into printable text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        return "".join(text_parts)

    return str(content)


class AgentOrchestrator:
    """Coordinate graph execution and streaming."""

    def __init__(self, chat_model, mcp_clients):
        mcp_tools = [build_mcp_tool(client) for client in mcp_clients]
        self._graph = build_graph(chat_model, mcp_tools)
        self._tool_descriptions = {
            tool.name: tool.description for tool in mcp_tools if tool.description
        }

    def _tool_display_label(self, tool_name: str) -> str:
        """Resolve a human-friendly label for tool status messages."""
        descriptions = getattr(self, "_tool_descriptions", {})
        return descriptions.get(tool_name, tool_name)

    async def run(
        self,
        *,
        prompt: str,
        channel: str,
        auth_mode: str,
        user_id: str,
        mcp_user_tokens: dict[str, str] | None = None,
        history: list[BaseMessage] | None = None,
    ) -> str:
        """Execute one complete run and return final text."""
        invocation_id = str(uuid.uuid4())[:8]
        set_log_context(
            invocation_id=invocation_id, channel=channel, mode=auth_mode, user_id=user_id
        )

        state = {
            "messages": (history or []) + [HumanMessage(content=prompt)],
            "auth_mode": auth_mode,
            "user_id": user_id,
            "mcp_user_tokens": mcp_user_tokens or {},
        }
        logger.info("Starting non-streaming run")
        result = await self._graph.ainvoke(state)
        return _stringify_stream_chunk_content(result["messages"][-1].content)

    async def stream(
        self,
        *,
        prompt: str,
        channel: str,
        auth_mode: str,
        user_id: str,
        mcp_user_tokens: dict[str, str] | None = None,
        history: list[BaseMessage] | None = None,
    ) -> AsyncIterator[str]:
        """Yield streaming updates from graph execution."""
        invocation_id = str(uuid.uuid4())[:8]
        set_log_context(
            invocation_id=invocation_id, channel=channel, mode=auth_mode, user_id=user_id
        )

        state = {
            "messages": (history or []) + [HumanMessage(content=prompt)],
            "auth_mode": auth_mode,
            "user_id": user_id,
            "mcp_user_tokens": mcp_user_tokens or {},
        }

        async for event in self._graph.astream_events(state, version="v2"):
            event_name = event.get("event", "")
            if event_name == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and getattr(chunk, "content", ""):
                    text = _stringify_stream_chunk_content(chunk.content)
                    if text:
                        yield text
            elif event_name == "on_tool_start":
                tool_name = event.get("name", "mcp_tool")
                tool_label = self._tool_display_label(tool_name)
                yield f"\n[tool] Querying {tool_label}...\n"
            elif event_name == "on_tool_end":
                tool_name = event.get("name", "mcp_tool")
                tool_label = self._tool_display_label(tool_name)
                yield f"\n[tool] {tool_label} response received.\n"
