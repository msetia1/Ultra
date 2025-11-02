"""Context models for calendar agents."""

from typing import Any, Optional
from pydantic import BaseModel


class CalendarContext(BaseModel):
    """Shared context for calendar agents."""
    week_id: str
    user_id: str
    week_snapshot: dict[str, Any]  # Complete week data with events
    event_locators: dict[str, dict]  # event_id -> EventDayLocator mapping
    conversation_history: Optional[str] = None  # Recent conversation turns
    agent_outputs: dict[str, Any] = {}  # Shared state for patches and SSE events

    class Config:
        arbitrary_types_allowed = True
