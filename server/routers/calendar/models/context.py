"""Context models for calendar agents."""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class CalendarContext(BaseModel):
    """Shared context for calendar agents.

    Compatible with RunContextWrapper from OpenAI Agents SDK.
    """
    week_id: str
    user_id: str
    week_snapshot: dict[str, Any]  # Complete week data with events
    event_locators: dict[str, dict]  # event_id -> EventDayLocator mapping
    conversation_history: Optional[str] = None  # Recent conversation turns
    agent_outputs: dict[str, Any] = {}  # Shared state for patches and SSE events

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        """Initialize context with default agent_outputs structure."""
        super().__init__(**data)
        # Ensure agent_outputs has required keys for SSE streaming
        if "proposed_calendar_patches" not in self.agent_outputs:
            self.agent_outputs["proposed_calendar_patches"] = []
        if "immediate_sse_events" not in self.agent_outputs:
            self.agent_outputs["immediate_sse_events"] = []
