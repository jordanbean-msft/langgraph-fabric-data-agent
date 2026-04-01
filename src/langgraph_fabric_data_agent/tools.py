"""LangChain tools that proxy calls to Fabric MCP."""

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from langgraph_fabric_data_agent.auth import AuthContext
from langgraph_fabric_data_agent.fabric_mcp_client import FabricMcpClient


def build_fabric_tool(client: FabricMcpClient):
    """Build a LangChain tool for Fabric querying via MCP."""

    @tool("fabric_data_agent_query")
    async def fabric_data_agent_query(
        query: str,
        state: Annotated[dict, InjectedState],
    ) -> str:
        """Query the Fabric Data Agent MCP tool using natural language."""
        auth_context = AuthContext(
            mode=state["auth_mode"],
            user_id=state["user_id"],
            hosted_user_token=state.get("fabric_user_token"),
        )
        await client.initialize(auth_context)
        tools = await client.list_tools(auth_context)
        selected_tool_name = tools[0]["name"] if tools else "query"
        return await client.call_tool(
            tool_name=selected_tool_name,
            arguments={"query": query},
            auth_context=auth_context,
        )

    return fabric_data_agent_query
