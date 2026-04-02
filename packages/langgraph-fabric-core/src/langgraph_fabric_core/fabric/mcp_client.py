"""Strict MCP protocol client for Fabric Data Agent."""

import json
import logging
from typing import Any

import httpx

from langgraph_fabric_core.core.config import CoreSettings
from langgraph_fabric_core.fabric.auth import AuthContext, FabricTokenProvider

logger = logging.getLogger(__name__)


class FabricMcpClient:
    """JSON-RPC MCP client over streamable HTTP."""

    def __init__(self, settings: CoreSettings, token_provider: FabricTokenProvider):
        self._settings = settings
        self._token_provider = token_provider
        self._request_id = 0

    @staticmethod
    def _try_parse_jsonrpc_sse_event(event_data: str) -> dict[str, Any] | None:
        """Parse a single SSE data payload into a JSON-RPC message when possible."""
        payload = event_data.strip()
        if not payload or payload == "[DONE]":
            return None
        try:
            message = json.loads(payload)
        except json.JSONDecodeError:
            logger.debug("Ignoring non-JSON SSE event payload")
            return None
        return message if isinstance(message, dict) else None

    async def _read_streamable_http_response(
        self,
        response: httpx.Response,
        request_id: int,
    ) -> dict[str, Any]:
        """Read JSON-RPC output from streamable HTTP response formats."""
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            body = await response.aread()
            data = json.loads(body.decode("utf-8"))
            if isinstance(data, dict):
                if "result" in data or "error" in data:
                    if data.get("id") != request_id:
                        raise RuntimeError(
                            f"MCP response id mismatch: expected {request_id}, got {data.get('id')}"
                        )
                    return data
                raise RuntimeError("MCP JSON response missing JSON-RPC result/error")
            raise RuntimeError("MCP JSON response must be a JSON object")

        if "text/event-stream" not in content_type:
            raise RuntimeError(
                "MCP server must return streamable HTTP responses (application/json or text/event-stream)"
            )

        messages: list[dict[str, Any]] = []
        event_data_lines: list[str] = []

        async for line in response.aiter_lines():
            if not line:
                if event_data_lines:
                    message = self._try_parse_jsonrpc_sse_event("\n".join(event_data_lines))
                    if message is not None:
                        messages.append(message)
                    event_data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                event_data_lines.append(line.removeprefix("data:").strip())

        if event_data_lines:
            message = self._try_parse_jsonrpc_sse_event("\n".join(event_data_lines))
            if message is not None:
                messages.append(message)

        for message in reversed(messages):
            if message.get("id") == request_id and ("result" in message or "error" in message):
                return message

        raise RuntimeError("MCP stream ended without a JSON-RPC response message")

    async def _rpc(
        self, method: str, params: dict[str, Any], auth_context: AuthContext
    ) -> dict[str, Any]:
        token = await self._token_provider.get_token(auth_context)
        request_id = self._request_id + 1
        self._request_id = request_id
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
        }

        logger.info("MCP request method=%s id=%s", method, request_id)
        async with httpx.AsyncClient(
            timeout=self._settings.fabric_data_agent_timeout_seconds
        ) as client:
            async with client.stream(
                "POST",
                self._settings.fabric_data_agent_mcp_url,
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                data = await self._read_streamable_http_response(response, request_id)

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
                "clientInfo": {"name": "langgraph-fabric-core", "version": "0.1.0"},
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
