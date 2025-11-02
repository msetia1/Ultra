"""Context loader service for calendar agents."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from supabase import Client

logger = logging.getLogger(__name__)


class CalendarContextLoader:
    """Loads calendar context for agents."""

    def __init__(self, db_client: Client):
        self.db = db_client

    def load_week_context(
        self,
        week_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Load full week context including events and locators.

        Args:
            week_id: Week identifier (e.g., "2025-W09")
            user_id: User UUID

        Returns:
            Dict with week_snapshot, event_locators, and context object
        """
        try:
            logger.info(f"[CONTEXT_LOADER] Loading week context for {week_id}, user {user_id}")

            # Parse week_id to get date range
            year, week_num = self._parse_week_id(week_id)
            start_date, end_date = self._get_week_dates(year, week_num)

            logger.info(f"[CONTEXT_LOADER] Week range: {start_date} to {end_date}")

            # Fetch events for the week
            response = (
                self.db.table("calendar_events")
                .select("*")
                .eq("user_id", user_id)
                .gte("scheduled_date", start_date.isoformat())
                .lte("scheduled_date", end_date.isoformat())
                .order("scheduled_date", desc=False)
                .order("start_time", desc=False)
                .execute()
            )

            events = response.data
            logger.info(f"[CONTEXT_LOADER] Loaded {len(events)} events")

            # Build week snapshot
            week_snapshot = self._build_week_snapshot(start_date, end_date, events)

            # Build event locators
            event_locators = self._build_event_locators(events)

            # Build context object
            context = {
                "week_id": week_id,
                "user_id": user_id,
                "week_snapshot": week_snapshot,
                "event_locators": event_locators,
                "conversation_history": None,  # Will be populated by conversation manager
                "agent_outputs": {
                    "proposed_calendar_patches": [],
                    "immediate_sse_events": [],
                },
            }

            return context

        except Exception as e:
            logger.error(f"[CONTEXT_LOADER] Failed to load context: {e}", exc_info=True)
            raise

    def _parse_week_id(self, week_id: str) -> tuple[int, int]:
        """Parse week_id like '2025-W09' into (year, week_num)."""
        parts = week_id.split("-W")
        if len(parts) != 2:
            raise ValueError(f"Invalid week_id format: {week_id}")
        return int(parts[0]), int(parts[1])

    def _get_week_dates(self, year: int, week_num: int) -> tuple[datetime, datetime]:
        """Get start and end dates for a given ISO week."""
        # ISO week 1 is the first week with Thursday in it
        jan_4 = datetime(year, 1, 4)
        week_1_start = jan_4 - timedelta(days=jan_4.weekday())
        target_week_start = week_1_start + timedelta(weeks=week_num - 1)
        target_week_end = target_week_start + timedelta(days=6)
        return target_week_start, target_week_end

    def _build_week_snapshot(
        self,
        start_date: datetime,
        end_date: datetime,
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build structured week snapshot with events organized by day."""
        days = []
        current = start_date

        # Create events map by date
        events_by_date = {}
        for event in events:
            date_str = event["scheduled_date"]
            if date_str not in events_by_date:
                events_by_date[date_str] = []
            events_by_date[date_str].append(event)

        # Build day structures
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            day_events = events_by_date.get(date_str, [])

            days.append({
                "date": date_str,
                "day_of_week": current.strftime("%A"),
                "events": day_events,
            })

            current += timedelta(days=1)

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "days": days,
        }

    def _build_event_locators(self, events: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """Build event locator map (event_id -> date locator)."""
        locators = {}
        for event in events:
            locators[event["id"]] = {
                "scheduled_date": event["scheduled_date"],
                "anchor": None,  # Could add position hints here
            }
        return locators
