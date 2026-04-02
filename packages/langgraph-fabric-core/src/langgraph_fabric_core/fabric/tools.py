"""LangChain tools that proxy calls to Fabric MCP."""

import logging
from typing import Annotated

import httpx
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import InjectedState

from langgraph_fabric_core.fabric.auth import AuthContext
from langgraph_fabric_core.fabric.mcp_client import FabricMcpClient

logger = logging.getLogger(__name__)


def _resolve_query_argument_name(tool_definition: dict) -> str:
    """Resolve the query argument field from MCP tool input schema."""
    input_schema = tool_definition.get("inputSchema")
    if not isinstance(input_schema, dict):
        return "query"

    properties = input_schema.get("properties")
    if not isinstance(properties, dict):
        return "query"

    preferred_names = ("userQuestion", "query", "prompt", "question")
    for name in preferred_names:
        if name in properties:
            return name

    required = input_schema.get("required")
    if isinstance(required, list):
        for field in required:
            if isinstance(field, str) and field in properties:
                return field

    for field in properties:
        if isinstance(field, str):
            return field

    return "query"


def build_fabric_tool(client: FabricMcpClient):
    """Build a LangChain tool for Fabric querying via MCP."""

    async def fabric_data_agent_query(
        query: str,
        state: Annotated[dict, InjectedState],
    ) -> str:
        """Query the Fabric Data Agent MCP tool using natural language."""
        auth_context = AuthContext(
            mode=state["auth_mode"],
            user_id=state["user_id"],
            user_token=state.get("fabric_user_token"),
        )

        try:
            await client.initialize(auth_context)
            tools = await client.list_tools(auth_context)
            selected_tool = tools[0] if tools else {"name": "query"}
            selected_tool_name = selected_tool.get("name", "query")
            query_argument_name = _resolve_query_argument_name(selected_tool)
            return await client.call_tool(
                tool_name=selected_tool_name,
                arguments={query_argument_name: query},
                auth_context=auth_context,
            )
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.exception("Fabric Data Agent query failed")
            return f"Fabric Data Agent query failed: {exc}"

    return StructuredTool.from_function(
        coroutine=fabric_data_agent_query,
        name="fabric_data_agent_query",
        description="Query the Fabric Data Agent MCP tool using natural language",
    )
