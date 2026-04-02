"""FastAPI application surface."""

import base64
import json
import logging
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

logger = logging.getLogger(__name__)


def _extract_user_id(token: str | None) -> str:
    """Extract user identity from JWT claims for correlation logging.

    The token is not validated here; it will be validated by Fabric when
    the request is forwarded. This extracts only the identity claim needed
    for structured log correlation.
    """
    if not token:
        return "local-user"
    try:
        payload_part = token.split(".")[1]
        padding = (4 - len(payload_part) % 4) % 4
        payload = json.loads(base64.b64decode(payload_part + "=" * padding))
        return (
            payload.get("preferred_username")
            or payload.get("upn")
            or payload.get("sub")
            or "unknown"
        )
    except Exception:
        logger.debug("Could not extract user identity from token", exc_info=True)
        return "unknown"


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
    fabric_user_token: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    orchestrator = get_orchestrator()
    auth_mode = "hosted" if request.fabric_user_token else "local"
    user_id = _extract_user_id(request.fabric_user_token)

    async def event_stream() -> AsyncIterator[bytes]:
        async for chunk in orchestrator.stream(
            prompt=request.prompt,
            channel="api",
            auth_mode=auth_mode,
            user_id=user_id,
            fabric_user_token=request.fabric_user_token,
        ):
            yield f"data: {chunk}\n\n".encode()
        yield b"event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
