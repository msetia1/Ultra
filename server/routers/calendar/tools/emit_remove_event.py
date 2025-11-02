"""Tool for emitting remove event patches."""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict
from agents import function_tool, RunContextWrapper
from ..models import CalendarRemoveEventPatch, EventDayLocator, CalendarContext

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
def emit_remove_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    event_id: str,
    date: str,
) -> Dict[str, Any]:
    """Emit a patch to remove a calendar event.

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        event_id: UUID of event to remove
        date: Scheduled date of event (YYYY-MM-DD)

    Returns:
        Dict with status and patch_id
    """
    try:
        # Unwrap context
        context = _resolve_context(wrapper)

        logger.info(f"[EMIT_REMOVE_EVENT] Creating patch for event {event_id}")

        # Create target day locator
        target_day = EventDayLocator(
            scheduled_date=datetime.strptime(date, "%Y-%m-%d").date(),
            anchor=None,
        )

        # Generate patch
        patch_id = str(uuid.uuid4())
        patch = CalendarRemoveEventPatch(
            op="remove_event",
            target_day=target_day,
            event_id=event_id,
            patch_id=patch_id,
        )

        # Add to context proposed patches
        context.agent_outputs["proposed_calendar_patches"].append(patch.model_dump(mode="json"))

        # Queue SSE event for streaming
        context.agent_outputs["immediate_sse_events"].append({
            "type": "patch_proposed",
            "patch": patch.model_dump(mode="json"),
        })

        logger.info(f"[EMIT_REMOVE_EVENT] Queued patch {patch_id}")

        return {
            "status": "queued",
            "patch_id": patch_id,
            "message": f"Created remove event patch for {event_id}",
        }

    except Exception as e:
        logger.error(f"[EMIT_REMOVE_EVENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
