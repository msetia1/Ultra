"""Pydantic models for calendar event patches."""

from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field


# Patch operation types
CalendarPatchOperation = Literal[
    "add_event",
    "remove_event",
    "modify_event",
    "move_event",
]


class EventInsertionAnchor(BaseModel):
    """Placement hint for inserting or moving events within a day."""
    relation: Literal["start", "end", "before", "after"]
    event_id: Optional[str] = None  # Required for 'before'/'after', null for 'start'/'end'


class EventDayLocator(BaseModel):
    """Identifies a day for event placement."""
    scheduled_date: date  # YYYY-MM-DD
    anchor: Optional[EventInsertionAnchor] = None


class CalendarEvent(BaseModel):
    """Simple calendar event structure."""
    title: str
    description: str = ""
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM (24-hour)
    end_time: str  # HH:MM (24-hour)
    event_id: Optional[str] = None  # Null for new events, UUID for existing


class EventFieldPatch(BaseModel):
    """Field-level diff for event modifications."""
    op_id: str
    operation: Literal["modify_field"]
    field: str
    from_value: Optional[str | int | float | bool] = None
    to_value: Optional[str | int | float | bool] = None


# Base patch class
class CalendarPatchBase(BaseModel):
    """Base class for all calendar patches."""
    op: CalendarPatchOperation
    target_day: EventDayLocator
    patch_id: Optional[str] = None  # Assigned during emission


# Specific patch operations
class CalendarAddEventPatch(CalendarPatchBase):
    """Patch to add a new event."""
    op: Literal["add_event"]
    complete_event: CalendarEvent
    insertion_hint: EventInsertionAnchor


class CalendarRemoveEventPatch(CalendarPatchBase):
    """Patch to remove an existing event."""
    op: Literal["remove_event"]
    event_id: str


class CalendarModifyEventPatch(CalendarPatchBase):
    """Patch to modify event fields."""
    op: Literal["modify_event"]
    event_id: str
    field_patches: list[EventFieldPatch]


class CalendarMoveEventPatch(CalendarPatchBase):
    """Patch to move event to different date/time."""
    op: Literal["move_event"]
    event_id: str
    from_day: EventDayLocator
    to_day: EventDayLocator
    post_move_adjustments: Optional[list[EventFieldPatch]] = None


# Union type for all patches
CalendarPatch = (
    CalendarAddEventPatch
    | CalendarRemoveEventPatch
    | CalendarModifyEventPatch
    | CalendarMoveEventPatch
)
