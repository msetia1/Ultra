"""Tool for emitting add event patches."""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict
from agents import function_tool, RunContextWrapper
from ..models import CalendarAddEventPatch, CalendarEvent, EventDayLocator, EventInsertionAnchor, CalendarContext

logger = logging.getLogger(__name__)


def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap RunContextWrapper to get CalendarContext.

    The Agents SDK may wrap context multiple times during nested agent calls.
    This function recursively unwraps to find the actual CalendarContext.
    """
    context = wrapper
    guard = 4  # Prevent infinite loops
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    return context


@function_tool
def emit_add_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> Dict[str, Any]:
    """Emit a patch to add a new calendar event.

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        title: Event title
        date: Scheduled date (YYYY-MM-DD)
        start_time: Start time (HH:MM in 24-hour format)
        end_time: End time (HH:MM in 24-hour format)
        description: Optional event description

    Returns:
        Dict with status and patch_id
    """
    try:
        # Unwrap context
        context = _resolve_context(wrapper)

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
        context.agent_outputs["proposed_calendar_patches"].append(patch.model_dump(mode="json"))

        # Queue SSE event for streaming
        context.agent_outputs["immediate_sse_events"].append({
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
