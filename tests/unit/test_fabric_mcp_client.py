import pytest
import respx
from httpx import Response

from langgraph_fabric_data_agent.fabric.auth import AuthContext
from langgraph_fabric_data_agent.fabric.mcp_client import FabricMcpClient


class FakeTokenProvider:
    async def get_token(self, _context: AuthContext) -> str:
        return "fake-token"


@pytest.mark.asyncio
@respx.mock
async def test_list_and_call_tool(settings_fixture):
    client = FabricMcpClient(settings_fixture, FakeTokenProvider())
    auth = AuthContext(mode="local", user_id="u1")

    respx.post(settings_fixture.fabric_data_agent_mcp_url).mock(
        side_effect=[
            Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}}),
            Response(200, json={"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "query"}]}}),
            Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {"content": [{"type": "text", "text": "hello"}]},
                },
            ),
        ]
    )

    await client.initialize(auth)
    tools = await client.list_tools(auth)
    text = await client.call_tool(tool_name="query", arguments={"query": "hi"}, auth_context=auth)

    assert tools[0]["name"] == "query"
    assert text == "hello"
