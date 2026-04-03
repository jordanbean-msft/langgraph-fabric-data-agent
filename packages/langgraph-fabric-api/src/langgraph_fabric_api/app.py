"""FastAPI application factory."""

from fastapi import FastAPI

from langgraph_fabric_api.routes import chat, health

app = FastAPI(title="LangGraph Fabric Data Agent")

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
