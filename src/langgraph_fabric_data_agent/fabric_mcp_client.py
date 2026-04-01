"""Strict MCP protocol client for Fabric Data Agent."""

import logging
from typing import Any

import httpx

from langgraph_fabric_data_agent.auth import AuthContext, FabricTokenProvider
from langgraph_fabric_data_agent.config import AppSettings

logger = logging.getLogger(__name__)


class FabricMcpClient:
    """Minimal JSON-RPC MCP client over HTTP."""

    def __init__(self, settings: AppSettings, token_provider: FabricTokenProvider):
        self._settings = settings
        self._token_provider = token_provider
        self._request_id = 0

    async def _rpc(self, method: str, params: dict[str, Any], auth_context: AuthContext) -> dict[str, Any]:
        token = await self._token_provider.get_token(auth_context)
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.info("MCP request method=%s id=%s", method, self._request_id)
        async with httpx.AsyncClient(timeout=self._settings.fabric_data_agent_timeout_seconds) as client:
            response = await client.post(self._settings.fabric_data_agent_mcp_url, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        return data.get("result", {})

    async def initialize(self, auth_context: AuthContext) -> None:
        """Initialize MCP session."""
        await self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "langgraph-fabric-data-agent", "version": "0.1.0"},
            },
            auth_context,
        )

    async def list_tools(self, auth_context: AuthContext) -> list[dict[str, Any]]:
        """Return MCP tools exposed by Fabric Data Agent."""
        result = await self._rpc("tools/list", {}, auth_context)
        return result.get("tools", [])

    async def call_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        auth_context: AuthContext,
    ) -> str:
        """Call an MCP tool and return text content."""
        result = await self._rpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
            auth_context,
        )
        content = result.get("content", [])
        text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
        return "\n".join(part for part in text_parts if part)
