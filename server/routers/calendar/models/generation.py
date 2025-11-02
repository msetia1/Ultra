"""Pydantic models for week generation."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CalendarEventGeneration(BaseModel):
    """Model for a generated calendar event."""
    title: str = Field(description="Event title")
    description: str = Field(default="", description="Event description/details")
    scheduled_date: str = Field(description="Event date in YYYY-MM-DD format")
    start_time: str = Field(description="Start time in HH:MM format (24-hour)")
    end_time: str = Field(description="End time in HH:MM format (24-hour)")

    # Optional metadata for context
    event_type: Optional[str] = Field(default=None, description="Type of event (e.g., 'meeting', 'workout', 'task')")
    priority: Optional[str] = Field(default=None, description="Event priority (e.g., 'high', 'medium', 'low')")


class WeekEventsGeneration(BaseModel):
    """Container for all generated events in a week."""
    events: List[CalendarEventGeneration] = Field(description="List of generated calendar events for the week")


class WeekGenerationRequest(BaseModel):
    """Request model for week generation endpoint."""
    user_goals: Optional[str] = Field(default=None, description="User's goals or focus areas for the week")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="Additional user context (preferences, constraints, etc.)")
    existing_events: Optional[List[Dict[str, Any]]] = Field(default=None, description="Existing events to consider when scheduling")
