"""LangChain tools that proxy calls to MCP servers."""

import logging
from typing import Annotated

import httpx
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import InjectedState

from langgraph_fabric_core.mcp.auth import AuthContext
from langgraph_fabric_core.mcp.client import McpClient

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


def build_mcp_tool(client: McpClient):
    """Build a LangChain tool for querying a specific MCP server."""

    server = client.server_config
    tool_name = f"mcp_{server.name}"

    async def mcp_query(
        query: str,
        state: Annotated[dict, InjectedState],
    ) -> str:
        """Query this MCP server using natural language."""
        tokens = state.get("mcp_user_tokens") or {}
        if not isinstance(tokens, dict):
            tokens = {}

        auth_context = AuthContext(
            mode=state["auth_mode"],
            user_id=state["user_id"],
            scope=server.scope,
            user_token=tokens.get(server.name),
        )

        try:
            await client.initialize(auth_context)
            tools = await client.list_tools(auth_context)
            selected_tool = tools[0] if tools else {"name": "query"}
            selected_tool_name = selected_tool.get("name", "query")
            query_argument_name = _resolve_query_argument_name(selected_tool)
            result = await client.call_tool(
                tool_name=selected_tool_name,
                arguments={query_argument_name: query},
                auth_context=auth_context,
            )
            logger.info("MCP server %s tool result: %s", server.name, result)
            return result
        except ValueError as exc:
            logger.warning("MCP server %s authentication unavailable: %s", server.name, exc)
            return (
                f"Authentication required for MCP server '{server.name}'. "
                "Sign in to the corresponding connection and retry."
            )
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.exception("MCP server %s query failed", server.name)
            return f"MCP server '{server.name}' query failed: {exc}"

    return StructuredTool.from_function(
        coroutine=mcp_query,
        name=tool_name,
        description=server.description,
    )
