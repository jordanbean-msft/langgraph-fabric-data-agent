"""FastAPI application surface."""

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import FastAPI
from langgraph_fabric_core.core.config import get_settings
from langgraph_fabric_core.fabric.auth import FabricTokenProvider
from langgraph_fabric_core.fabric.mcp_client import FabricMcpClient
from langgraph_fabric_core.graph.orchestrator import AgentOrchestrator
from langgraph_fabric_core.llm.factory import create_chat_model
from pydantic import BaseModel
from starlette.responses import StreamingResponse


@lru_cache(maxsize=1)
def get_orchestrator() -> AgentOrchestrator:
    """Build and cache the default orchestrator instance."""
    settings = get_settings()
    token_provider = FabricTokenProvider(settings)
    fabric_client = FabricMcpClient(settings, token_provider)
    chat_model = create_chat_model(settings)
    return AgentOrchestrator(chat_model, fabric_client)


app = FastAPI(title="LangGraph Fabric Data Agent")


class ChatRequest(BaseModel):
    prompt: str
    user_id: str = "local-user"
    fabric_user_token: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    orchestrator = get_orchestrator()
    auth_mode = "hosted" if request.fabric_user_token else "local"

    async def event_stream() -> AsyncIterator[bytes]:
        async for chunk in orchestrator.stream(
            prompt=request.prompt,
            channel="api",
            auth_mode=auth_mode,
            user_id=request.user_id,
            fabric_user_token=request.fabric_user_token,
        ):
            yield f"data: {chunk}\n\n".encode()
        yield b"event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
