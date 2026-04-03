"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Schema for chat request payload."""

    prompt: str
