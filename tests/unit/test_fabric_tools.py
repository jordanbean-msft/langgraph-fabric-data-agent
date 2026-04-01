from unittest.mock import AsyncMock

import pytest

from langgraph_fabric_data_agent.fabric.tools import build_fabric_tool


@pytest.mark.asyncio
async def test_build_fabric_tool_invokes_mcp_tool_with_state_auth_context() -> None:
    client = AsyncMock()
    client.list_tools.return_value = [
        {
            "name": "fabric_query",
            "inputSchema": {
                "type": "object",
                "properties": {"userQuestion": {"type": "string"}},
                "required": ["userQuestion"],
            },
        }
    ]
    client.call_tool.return_value = "customer results"

    tool = build_fabric_tool(client)
    state = {
        "auth_mode": "local",
        "user_id": "console-user",
        "fabric_user_token": None,
    }

    assert tool.coroutine is not None
    result = await tool.coroutine(query="top 5 customers", state=state)

    assert result == "customer results"
    client.initialize.assert_awaited_once()
    client.list_tools.assert_awaited_once()
    client.call_tool.assert_awaited_once_with(
        tool_name="fabric_query",
        arguments={"userQuestion": "top 5 customers"},
        auth_context=client.call_tool.await_args.kwargs["auth_context"],
    )
    auth_context = client.call_tool.await_args.kwargs["auth_context"]
    assert auth_context.mode == "local"
    assert auth_context.user_id == "console-user"
    assert auth_context.hosted_user_token is None


@pytest.mark.asyncio
async def test_build_fabric_tool_defaults_tool_name_when_mcp_list_is_empty() -> None:
    client = AsyncMock()
    client.list_tools.return_value = []
    client.call_tool.return_value = "ok"

    tool = build_fabric_tool(client)
    state = {
        "auth_mode": "hosted",
        "user_id": "hosted-user",
        "fabric_user_token": "token-123",
    }

    assert tool.coroutine is not None
    await tool.coroutine(query="sales", state=state)

    client.call_tool.assert_awaited_once_with(
        tool_name="query",
        arguments={"query": "sales"},
        auth_context=client.call_tool.await_args.kwargs["auth_context"],
    )
    auth_context = client.call_tool.await_args.kwargs["auth_context"]
    assert auth_context.mode == "hosted"
    assert auth_context.user_id == "hosted-user"
    assert auth_context.hosted_user_token == "token-123"


@pytest.mark.asyncio
async def test_build_fabric_tool_returns_error_message_on_mcp_failure() -> None:
    client = AsyncMock()
    client.list_tools.return_value = [{"name": "fabric_query", "inputSchema": {"properties": {"query": {}}}}]
    client.call_tool.side_effect = RuntimeError("upstream failure")

    tool = build_fabric_tool(client)
    state = {
        "auth_mode": "local",
        "user_id": "console-user",
        "fabric_user_token": None,
    }

    assert tool.coroutine is not None
    result = await tool.coroutine(query="sales", state=state)

    assert "Fabric Data Agent query failed:" in result
    assert "upstream failure" in result
