"""Streaming parser for calendar events from LLM JSON output.

Parses partial JSON from streaming text deltas to extract complete calendar events
as they become available during LLM token streaming.
"""

import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EventStreamingParser:
    """
    Parses partial JSON from streaming text deltas to extract complete calendar events
    as they become available during LLM token streaming.

    Pattern adapted from Trayne SessionStreamingParser for real-time event detection.
    """

    def __init__(self):
        self.accumulated_text = ""
        self.last_parsed_state = {}
        self.last_event_count = 0
        self.total_deltas_processed = 0

    def add_delta(self, delta_text: str) -> Dict[str, Any]:
        """
        Add new text delta and attempt to parse individual calendar events.
        Returns any newly available complete events.

        Args:
            delta_text: New text chunk from streaming LLM

        Returns:
            Dict with 'new_events' and 'event_indices' if new events detected, empty dict otherwise
        """
        self.total_deltas_processed += 1
        self.accumulated_text += delta_text

        # Debug logging for development
        if len(delta_text) > 0 and self.total_deltas_processed % 20 == 0:
            snippet = delta_text[-50:] if len(delta_text) > 50 else delta_text
            logger.debug(f"🔍 Delta snippet: {snippet}")

        # Try to parse the current accumulated text
        new_state = self._extract_partial_json()

        # Compare with last state to find new events
        new_fields = self._find_new_events(self.last_parsed_state, new_state)

        if new_fields:
            logger.debug(f"🆕 New events detected: {list(new_fields.keys())}")
            for key, value in new_fields.items():
                if isinstance(value, list):
                    logger.debug(f"   {key}: {len(value)} events")

        # Update last parsed state
        self.last_parsed_state = new_state.copy()

        return new_fields

    def _extract_partial_json(self) -> Dict[str, Any]:
        """
        Attempt to extract valid JSON structure from accumulated text.
        Handles incomplete JSON by finding complete events in the events array.

        Returns:
            Dict with 'events' key containing list of complete event objects
        """
        result = {}

        # Look for the events array
        match = re.search(r'"events"\s*:\s*\[', self.accumulated_text)
        if not match:
            return result

        # Find all complete event objects within the array
        events = []

        # Start from the beginning of events array
        start_pos = match.end()
        text_from_array = self.accumulated_text[start_pos:]

        # Track bracket depth to find complete objects
        depth = 0
        current_obj_start = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(text_from_array):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                if depth == 0:
                    current_obj_start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and current_obj_start != -1:
                    # Found a complete object
                    obj_text = text_from_array[current_obj_start:i+1]
                    try:
                        # Try to parse this individual event
                        event_obj = json.loads(obj_text)
                        events.append(event_obj)
                    except json.JSONDecodeError:
                        # Skip malformed objects
                        pass
                    current_obj_start = -1

        if events:
            result["events"] = events

        return result

    def _find_new_events(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare old and new states to find newly available events.
        Returns only the new events that weren't in the previous state.

        Args:
            old_state: Previous parsing state
            new_state: Current parsing state

        Returns:
            Dict with 'new_events' list and 'event_indices' list if new events found
        """
        new_fields = {}

        old_events = old_state.get("events", [])
        new_events = new_state.get("events", [])

        # Find events that are new (weren't in old state)
        if len(new_events) > len(old_events):
            # Get only the new events
            newly_added = new_events[len(old_events):]
            if newly_added:
                new_fields["new_events"] = newly_added
                new_fields["event_indices"] = list(range(len(old_events), len(new_events)))

        return new_fields

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current parsed state."""
        return self.last_parsed_state.copy()

    def get_current_content(self) -> str:
        """Get the current accumulated text content."""
        return self.accumulated_text

    def _is_event_complete(self, event: Dict[str, Any]) -> bool:
        """
        Check if an event has all required fields.

        Args:
            event: Event dictionary to validate

        Returns:
            True if event has all required fields
        """
        required_fields = ["title", "scheduled_date", "start_time", "end_time"]
        return all(field in event for field in required_fields)
