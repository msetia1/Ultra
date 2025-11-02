"""Tool for emitting add event patches."""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict
from ..models import CalendarAddEventPatch, CalendarEvent, EventDayLocator, EventInsertionAnchor

logger = logging.getLogger(__name__)


def emit_add_event_patch(
    context: Dict[str, Any],
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> Dict[str, Any]:
    """Emit a patch to add a new calendar event.

    Args:
        context: Shared calendar context
        title: Event title
        date: Scheduled date (YYYY-MM-DD)
        start_time: Start time (HH:MM in 24-hour format)
        end_time: End time (HH:MM in 24-hour format)
        description: Optional event description

    Returns:
        Dict with status and patch_id
    """
    try:
        logger.info(f"[EMIT_ADD_EVENT] Creating patch for '{title}' on {date}")

        # Create complete event
        event = CalendarEvent(
            title=title,
            description=description,
            date=date,
            start_time=start_time,
            end_time=end_time,
            event_id=None,  # Will be assigned on persistence
        )

        # Create target day locator
        target_day = EventDayLocator(
            scheduled_date=datetime.strptime(date, "%Y-%m-%d").date(),
            anchor=None,
        )

        # Default insertion hint: add at end of day
        insertion_hint = EventInsertionAnchor(
            relation="end",
            event_id=None,
        )

        # Generate patch
        patch_id = str(uuid.uuid4())
        patch = CalendarAddEventPatch(
            op="add_event",
            target_day=target_day,
            complete_event=event,
            insertion_hint=insertion_hint,
            patch_id=patch_id,
        )

        # Add to context proposed patches
        agent_outputs = context.get("agent_outputs", {})
        proposed_patches = agent_outputs.setdefault("proposed_calendar_patches", [])
        proposed_patches.append(patch.model_dump(mode="json"))

        # Queue SSE event for streaming
        immediate_events = agent_outputs.setdefault("immediate_sse_events", [])
        immediate_events.append({
            "type": "patch_proposed",
            "patch": patch.model_dump(mode="json"),
        })

        logger.info(f"[EMIT_ADD_EVENT] Queued patch {patch_id}")

        return {
            "status": "queued",
            "patch_id": patch_id,
            "message": f"Created add event patch for '{title}'",
        }

    except Exception as e:
        logger.error(f"[EMIT_ADD_EVENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
