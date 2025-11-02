"""Request models for calendar chat API."""

from typing import Optional
from pydantic import BaseModel


class CalendarChatRequest(BaseModel):
    """Request model for calendar chat endpoint."""
    message: str
    conversation_id: Optional[str] = None


class CalendarAcceptRequest(BaseModel):
    """Request model for accepting calendar patches."""
    patches: list[dict]  # List of patch objects
    conversation_id: Optional[str] = None
