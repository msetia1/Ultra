"""Overlap validation service for calendar events.

Detects and resolves time conflicts between events to ensure sequential scheduling.
"""

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, time, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class OverlapValidator:
    """Validates and fixes overlapping calendar events."""

    def __init__(self, min_buffer_minutes: int = 15):
        """
        Initialize validator.

        Args:
            min_buffer_minutes: Minimum buffer time between events in minutes
        """
        self.min_buffer_minutes = min_buffer_minutes

    def parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format to time object."""
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            logger.error(f"Invalid time format: {time_str}")
            raise

    def time_to_minutes(self, t: time) -> int:
        """Convert time object to minutes since midnight."""
        return t.hour * 60 + t.minute

    def minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time object."""
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=hours % 24, minute=mins)

    def events_overlap(
        self,
        event1_start: time,
        event1_end: time,
        event2_start: time,
        event2_end: time
    ) -> bool:
        """
        Check if two events overlap in time.

        Args:
            event1_start: First event start time
            event1_end: First event end time
            event2_start: Second event start time
            event2_end: Second event end time

        Returns:
            True if events overlap, False otherwise
        """
        # Convert to minutes for easier comparison
        e1_start = self.time_to_minutes(event1_start)
        e1_end = self.time_to_minutes(event1_end)
        e2_start = self.time_to_minutes(event2_start)
        e2_end = self.time_to_minutes(event2_end)

        # Events overlap if one starts before the other ends
        return not (e1_end <= e2_start or e2_end <= e1_start)

    def has_sufficient_buffer(
        self,
        event1_end: time,
        event2_start: time
    ) -> bool:
        """
        Check if there's sufficient buffer between consecutive events.

        Args:
            event1_end: First event end time
            event2_start: Second event start time

        Returns:
            True if buffer >= min_buffer_minutes
        """
        e1_end_min = self.time_to_minutes(event1_end)
        e2_start_min = self.time_to_minutes(event2_start)

        # Check if second event starts after first ends
        if e2_start_min < e1_end_min:
            return False

        buffer = e2_start_min - e1_end_min
        return buffer >= self.min_buffer_minutes

    def detect_overlaps(self, events: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        Detect all overlapping event pairs.

        Args:
            events: List of event dictionaries with scheduled_date, start_time, end_time

        Returns:
            List of tuples (index1, index2) indicating overlapping event pairs
        """
        overlaps = []

        # Group events by date
        events_by_date = defaultdict(list)
        for idx, event in enumerate(events):
            date = event.get("scheduled_date")
            if date:
                events_by_date[date].append((idx, event))

        # Check for overlaps within each date
        for date, date_events in events_by_date.items():
            for i in range(len(date_events)):
                for j in range(i + 1, len(date_events)):
                    idx1, event1 = date_events[i]
                    idx2, event2 = date_events[j]

                    try:
                        e1_start = self.parse_time(event1["start_time"])
                        e1_end = self.parse_time(event1["end_time"])
                        e2_start = self.parse_time(event2["start_time"])
                        e2_end = self.parse_time(event2["end_time"])

                        if self.events_overlap(e1_start, e1_end, e2_start, e2_end):
                            overlaps.append((idx1, idx2))
                            logger.warning(
                                f"⚠️ Overlap detected on {date}: "
                                f"Event {idx1} ({event1['start_time']}-{event1['end_time']}) "
                                f"overlaps Event {idx2} ({event2['start_time']}-{event2['end_time']})"
                            )
                    except (KeyError, ValueError) as e:
                        logger.error(f"Error checking overlap: {e}")
                        continue

        return overlaps

    def enforce_max_events_per_day(
        self,
        events: List[Dict[str, Any]],
        max_events_per_day: int = 3
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Enforce maximum number of events per day.

        If a day has more than max_events_per_day events, keep only the highest priority ones.

        Args:
            events: List of event dictionaries
            max_events_per_day: Maximum events allowed per day

        Returns:
            Tuple of (filtered_events, stats_dict)
        """
        if not events:
            return events, {"days_over_limit": 0, "events_removed": 0}

        stats = {
            "days_over_limit": 0,
            "events_removed": 0,
            "removed_by_day": {}
        }

        # Group events by date
        events_by_date = defaultdict(list)
        for idx, event in enumerate(events):
            date = event.get("scheduled_date")
            if date:
                events_by_date[date].append({"index": idx, "event": event})

        # Check each day and filter if needed
        filtered_events = []
        events_removed = []

        for date, date_events in events_by_date.items():
            if len(date_events) > max_events_per_day:
                stats["days_over_limit"] += 1

                # Sort by priority (high > medium > low) and keep top N
                priority_order = {"high": 3, "medium": 2, "low": 1, None: 0}
                sorted_events = sorted(
                    date_events,
                    key=lambda x: priority_order.get(x["event"].get("priority"), 0),
                    reverse=True
                )

                # Keep only top max_events_per_day
                kept = sorted_events[:max_events_per_day]
                removed = sorted_events[max_events_per_day:]

                stats["events_removed"] += len(removed)
                stats["removed_by_day"][date] = len(removed)

                logger.warning(
                    f"⚠️ Day {date} had {len(date_events)} events (max is {max_events_per_day}). "
                    f"Removed {len(removed)} lowest priority events."
                )

                for event_data in kept:
                    filtered_events.append(event_data["event"])

                for event_data in removed:
                    events_removed.append(event_data["event"].get("title", "Unknown"))
            else:
                # Keep all events for this day
                for event_data in date_events:
                    filtered_events.append(event_data["event"])

        if stats["events_removed"] > 0:
            logger.info(
                f"📊 Removed {stats['events_removed']} events from {stats['days_over_limit']} days "
                f"to enforce {max_events_per_day} events/day limit"
            )

        return filtered_events, stats

    def validate_and_fix_events(
        self,
        events: List[Dict[str, Any]],
        max_events_per_day: int = 4
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate events and fix any overlaps by adjusting times.

        Strategy:
        1. Enforce max events per day (remove lowest priority if over limit)
        2. Group events by date
        3. Sort by start time within each date
        4. For each event, if it overlaps with previous event:
           - Move start time to previous event's end time + buffer
           - Adjust end time to maintain duration (or cap at reasonable max)

        Args:
            events: List of event dictionaries
            max_events_per_day: Maximum events allowed per day (default 3)

        Returns:
            Tuple of (fixed_events, stats_dict)
        """
        if not events:
            return events, {"overlaps_detected": 0, "events_fixed": 0, "events_removed": 0}

        # Step 1: Enforce max events per day first
        events, limit_stats = self.enforce_max_events_per_day(events, max_events_per_day)

        stats = {
            "overlaps_detected": 0,
            "events_fixed": 0,
            "buffer_violations": 0,
            "events_removed": limit_stats.get("events_removed", 0),
            "days_over_limit": limit_stats.get("days_over_limit", 0)
        }

        # Step 2: Detect initial overlaps
        initial_overlaps = self.detect_overlaps(events)
        stats["overlaps_detected"] = len(initial_overlaps)

        if not initial_overlaps:
            logger.info("✅ No overlaps detected, all events are valid")
            return events, stats

        logger.info(f"🔧 Fixing {len(initial_overlaps)} overlapping event pairs")

        # Group events by date for fixing
        events_by_date = defaultdict(list)
        for idx, event in enumerate(events):
            date = event.get("scheduled_date")
            if date:
                events_by_date[date].append({"index": idx, "event": event.copy()})

        fixed_events = [None] * len(events)

        # Fix overlaps within each date
        for date, date_events in events_by_date.items():
            # Sort by start time
            date_events.sort(
                key=lambda x: self.parse_time(x["event"]["start_time"])
            )

            for i, event_data in enumerate(date_events):
                event = event_data["event"]
                original_idx = event_data["index"]

                if i == 0:
                    # First event doesn't need adjustment
                    fixed_events[original_idx] = event
                    continue

                # Check against previous event
                prev_event = date_events[i - 1]["event"]

                try:
                    current_start = self.parse_time(event["start_time"])
                    current_end = self.parse_time(event["end_time"])
                    prev_end = self.parse_time(prev_event["end_time"])

                    # Check if there's an overlap or insufficient buffer
                    if not self.has_sufficient_buffer(prev_end, current_start):
                        # Calculate event duration
                        current_start_min = self.time_to_minutes(current_start)
                        current_end_min = self.time_to_minutes(current_end)
                        duration = current_end_min - current_start_min

                        # Move start time to prev_end + buffer
                        new_start_min = self.time_to_minutes(prev_end) + self.min_buffer_minutes
                        new_end_min = new_start_min + duration

                        # Cap end time at reasonable limit (23:59)
                        if new_end_min > 1439:  # 23:59 in minutes
                            new_end_min = 1439
                            # Also adjust start if needed to maintain some duration
                            min_duration = 30  # At least 30 min event
                            new_start_min = max(new_end_min - duration, new_end_min - min_duration)

                        # Update event times
                        event["start_time"] = self.minutes_to_time(new_start_min).strftime("%H:%M")
                        event["end_time"] = self.minutes_to_time(new_end_min).strftime("%H:%M")

                        stats["events_fixed"] += 1
                        logger.info(
                            f"🔧 Fixed event {original_idx} on {date}: "
                            f"{current_start.strftime('%H:%M')} → {event['start_time']}"
                        )

                    fixed_events[original_idx] = event

                except (KeyError, ValueError) as e:
                    logger.error(f"Error fixing event {original_idx}: {e}")
                    # Keep original event if fixing fails
                    fixed_events[original_idx] = event

        logger.info(f"✅ Validation complete: {stats['events_fixed']} events adjusted")

        # Verify no overlaps remain
        final_overlaps = self.detect_overlaps(fixed_events)
        if final_overlaps:
            logger.warning(f"⚠️ {len(final_overlaps)} overlaps remain after fixing")
        else:
            logger.info("✅ All overlaps successfully resolved")

        return fixed_events, stats


# Convenience function for easy import
def validate_events(
    events: List[Dict[str, Any]],
    min_buffer_minutes: int = 15,
    max_events_per_day: int = 4
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Validate and fix overlapping events.

    Args:
        events: List of event dictionaries
        min_buffer_minutes: Minimum buffer between events
        max_events_per_day: Maximum events allowed per day

    Returns:
        Tuple of (fixed_events, validation_stats)
    """
    validator = OverlapValidator(min_buffer_minutes=min_buffer_minutes)
    return validator.validate_and_fix_events(events, max_events_per_day=max_events_per_day)
