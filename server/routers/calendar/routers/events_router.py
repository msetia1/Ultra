"""Events router for fetching calendar events."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from integrations.supabase_service import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Events"])


def _parse_week_id(week_id: str) -> tuple[int, int]:
    """Parse week_id like '2025-W09' into (year, week_num)."""
    parts = week_id.split("-W")
    if len(parts) != 2:
        raise ValueError(f"Invalid week_id format: {week_id}")
    return int(parts[0]), int(parts[1])


def _get_week_dates(year: int, week_num: int) -> tuple[datetime, datetime]:
    """Get start and end dates for a given ISO week."""
    # ISO week 1 is the first week with Thursday in it
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.weekday())
    target_week_start = week_1_start + timedelta(weeks=week_num - 1)
    target_week_end = target_week_start + timedelta(days=6)
    return target_week_start, target_week_end


@router.get("/events")
async def get_week_events(
    week_id: str = Query(..., description="Week identifier (e.g., '2025-W09')"),
    user_id: str = "00000000-0000-0000-0000-000000000000",  # TODO: Get from auth
):
    """
    Fetch calendar events for a specific week.

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        user_id: User UUID (TODO: from auth)

    Returns:
        List of calendar events for the week
    """
    try:
        logger.info(f"[EVENTS_ROUTER] Fetching events for week {week_id}, user {user_id}")

        # Parse week_id to get date range
        try:
            year, week_num = _parse_week_id(week_id)
            week_start, week_end = _get_week_dates(year, week_num)
            logger.info(f"[EVENTS_ROUTER] Week range: {week_start.date()} to {week_end.date()}")
        except ValueError as e:
            logger.error(f"[EVENTS_ROUTER] Invalid week_id format: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        # Get database client
        db_client = get_supabase()

        # Fetch events from database
        try:
            response = (
                db_client.table("calendar_events")
                .select("*")
                .eq("user_id", user_id)
                .gte("scheduled_date", week_start.date().isoformat())
                .lte("scheduled_date", week_end.date().isoformat())
                .order("scheduled_date", desc=False)
                .order("start_time", desc=False)
                .execute()
            )

            events = response.data or []
            logger.info(f"[EVENTS_ROUTER] Found {len(events)} events for week {week_id}")

            # Convert time objects to strings for JSON serialization
            for event in events:
                # Convert date to string
                if isinstance(event.get("scheduled_date"), datetime):
                    event["scheduled_date"] = event["scheduled_date"].strftime("%Y-%m-%d")

                # Convert time objects to HH:MM format
                for time_field in ["start_time", "end_time"]:
                    if time_field in event and event[time_field]:
                        time_val = event[time_field]
                        # Handle various time formats
                        if isinstance(time_val, str):
                            # Already a string, ensure HH:MM format
                            if len(time_val) == 8:  # HH:MM:SS
                                event[time_field] = time_val[:5]
                        else:
                            # Convert to string
                            event[time_field] = str(time_val)[:5]

            return {"events": events}

        except Exception as e:
            logger.error(f"[EVENTS_ROUTER] Database error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EVENTS_ROUTER] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
