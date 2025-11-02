"""Database helper utilities for integration tests."""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from supabase import Client


def get_events_for_week(
    db: Client,
    user_id: str,
    week_id: str,
) -> List[Dict[str, Any]]:
    """Get all calendar events for a given week.

    Args:
        db: Supabase client
        user_id: User UUID
        week_id: Week identifier (e.g., "2025-W09")

    Returns:
        List of event records
    """
    # Parse week_id to get date range
    year, week_num = _parse_week_id(week_id)
    start_date, end_date = _get_week_dates(year, week_num)

    response = (
        db.table("calendar_events")
        .select("*")
        .eq("user_id", user_id)
        .gte("scheduled_date", start_date.isoformat())
        .lte("scheduled_date", end_date.isoformat())
        .order("scheduled_date", desc=False)
        .execute()
    )

    return response.data


def get_event_by_id(
    db: Client,
    event_id: str,
) -> Optional[Dict[str, Any]]:
    """Get a single event by ID.

    Args:
        db: Supabase client
        event_id: Event UUID

    Returns:
        Event record or None if not found
    """
    response = (
        db.table("calendar_events")
        .select("*")
        .eq("id", event_id)
        .execute()
    )

    return response.data[0] if response.data else None


def event_exists(
    db: Client,
    event_id: str,
) -> bool:
    """Check if an event exists in the database.

    Args:
        db: Supabase client
        event_id: Event UUID

    Returns:
        True if event exists
    """
    return get_event_by_id(db, event_id) is not None


def find_event_by_title(
    db: Client,
    user_id: str,
    title: str,
) -> Optional[Dict[str, Any]]:
    """Find an event by title.

    Args:
        db: Supabase client
        user_id: User UUID
        title: Event title to search for

    Returns:
        Event record or None if not found
    """
    response = (
        db.table("calendar_events")
        .select("*")
        .eq("user_id", user_id)
        .eq("title", title)
        .execute()
    )

    return response.data[0] if response.data else None


def verify_event_fields(
    event: Dict[str, Any],
    expected_fields: Dict[str, Any],
) -> bool:
    """Verify that an event has the expected field values.

    Args:
        event: Event record from database
        expected_fields: Dict of field_name -> expected_value

    Returns:
        True if all fields match
    """
    for field, expected_value in expected_fields.items():
        if event.get(field) != expected_value:
            return False

    return True


def get_conversation_turns(
    db: Client,
    conversation_id: str,
) -> List[Dict[str, Any]]:
    """Get all turns for a conversation.

    Args:
        db: Supabase client
        conversation_id: Conversation UUID

    Returns:
        List of turn records
    """
    response = (
        db.table("calendar_conversation_turns")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return response.data


def _parse_week_id(week_id: str) -> tuple[int, int]:
    """Parse week_id like '2025-W09' into (year, week_num)."""
    parts = week_id.split("-W")
    if len(parts) != 2:
        raise ValueError(f"Invalid week_id format: {week_id}")
    return int(parts[0]), int(parts[1])


def _get_week_dates(year: int, week_num: int) -> tuple[date, date]:
    """Get start and end dates for a given ISO week."""
    from datetime import datetime

    # ISO week 1 is the first week with Thursday in it
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4.date() - timedelta(days=jan_4.weekday())
    target_week_start = week_1_start + timedelta(weeks=week_num - 1)
    target_week_end = target_week_start + timedelta(days=6)
    return target_week_start, target_week_end
