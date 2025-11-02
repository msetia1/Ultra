"""Tool for emitting move event patches."""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from ..models import CalendarMoveEventPatch, EventDayLocator, EventFieldPatch

logger = logging.getLogger(__name__)


def emit_move_event_patch(
    context: Dict[str, Any],
    event_id: str,
    from_date: str,
    to_date: str,
    adjust_start_time: Optional[str] = None,
    adjust_end_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit a patch to move a calendar event to a different date.

    Args:
        context: Shared calendar context
        event_id: UUID of event to move
        from_date: Current date (YYYY-MM-DD)
        to_date: New date (YYYY-MM-DD)
        adjust_start_time: Optional new start time (HH:MM)
        adjust_end_time: Optional new end time (HH:MM)

    Returns:
        Dict with status and patch_id
    """
    try:
        logger.info(f"[EMIT_MOVE_EVENT] Creating patch to move event {event_id} from {from_date} to {to_date}")

        # Create locators
        from_day = EventDayLocator(
            scheduled_date=datetime.strptime(from_date, "%Y-%m-%d").date(),
            anchor=None,
        )
        to_day = EventDayLocator(
            scheduled_date=datetime.strptime(to_date, "%Y-%m-%d").date(),
            anchor=None,
        )

        # Build post-move time adjustments if provided
        post_move_adjustments = []
        if adjust_start_time:
            post_move_adjustments.append(
                EventFieldPatch(
                    op_id=uuid.uuid4().hex,
                    operation="modify_field",
                    field="start_time",
                    from_value=None,  # Will be determined from event
                    to_value=adjust_start_time,
                )
            )
        if adjust_end_time:
            post_move_adjustments.append(
                EventFieldPatch(
                    op_id=uuid.uuid4().hex,
                    operation="modify_field",
                    field="end_time",
                    from_value=None,
                    to_value=adjust_end_time,
                )
            )

        # Generate patch
        patch_id = str(uuid.uuid4())
        patch = CalendarMoveEventPatch(
            op="move_event",
            target_day=to_day,
            event_id=event_id,
            from_day=from_day,
            to_day=to_day,
            post_move_adjustments=post_move_adjustments if post_move_adjustments else None,
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

        logger.info(f"[EMIT_MOVE_EVENT] Queued patch {patch_id}")

        return {
            "status": "queued",
            "patch_id": patch_id,
            "message": f"Created move event patch from {from_date} to {to_date}",
        }

    except Exception as e:
        logger.error(f"[EMIT_MOVE_EVENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }
