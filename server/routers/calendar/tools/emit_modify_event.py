"""Tool for emitting modify event patches using Morph API."""

import uuid
import json
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from deepdiff import DeepDiff
from agents import function_tool, RunContextWrapper
from ..models import CalendarModifyEventPatch, EventDayLocator, EventFieldPatch, CalendarContext
from ..services.openrouter_client import get_openrouter_client

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
async def emit_modify_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    event_id: str,
    date: str,
    instruction: str,
    lazy_edit: str,
) -> Dict[str, Any]:
    """Emit a patch to modify event fields using Morph API.

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        event_id: UUID of event to modify
        date: Scheduled date of event (YYYY-MM-DD)
        instruction: First-person description of change (e.g., "I'm changing the time from 2pm to 3pm")
        lazy_edit: JSON string with minimal changes (e.g., '{"start_time": "15:00"}')

    Returns:
        Dict with status, patch_id, and field_patch_count
    """
    try:
        # Unwrap context
        context = _resolve_context(wrapper)

        # Parse lazy_edit JSON string to dict
        lazy_edit_dict = json.loads(lazy_edit)

        logger.info(f"[EMIT_MODIFY_EVENT] Creating patch for event {event_id}")

        # Find original event in week snapshot
        original_event = _find_event_by_id(context.week_snapshot, event_id)
        if not original_event:
            raise ValueError(f"Event {event_id} not found in week snapshot")

        logger.info(f"[EMIT_MODIFY_EVENT] Found event: {original_event.get('title')}")

        # Call Morph API to merge changes
        client = get_openrouter_client()
        original_json = json.dumps(original_event, indent=2)
        lazy_edit_json = json.dumps(lazy_edit_dict)

        morph_prompt = f"<instruction>{instruction}</instruction>\n<code>{original_json}</code>\n<update>{lazy_edit_json}</update>"

        logger.info(f"[EMIT_MODIFY_EVENT] Calling Morph API")
        response = await client.chat_completion(
            model="morph/morph-v3-large",
            messages=[{"role": "user", "content": morph_prompt}],
            stream=False,
        )

        merged_json = response.choices[0].message.content
        merged_event = json.loads(merged_json)

        logger.info(f"[EMIT_MODIFY_EVENT] Morph merge successful")

        # Generate field patches by diffing
        field_patches = _generate_field_patches(original_event, merged_event)
        logger.info(f"[EMIT_MODIFY_EVENT] Generated {len(field_patches)} field patches")

        # Create target day locator
        target_day = EventDayLocator(
            scheduled_date=datetime.strptime(date, "%Y-%m-%d").date(),
            anchor=None,
        )

        # Generate patch
        patch_id = str(uuid.uuid4())
        patch = CalendarModifyEventPatch(
            op="modify_event",
            target_day=target_day,
            event_id=event_id,
            field_patches=field_patches,
            patch_id=patch_id,
        )

        # Add to context proposed patches
        context.agent_outputs["proposed_calendar_patches"].append(patch.model_dump(mode="json"))

        # Queue SSE event for streaming
        context.agent_outputs["immediate_sse_events"].append({
            "type": "patch_proposed",
            "patch": patch.model_dump(mode="json"),
        })

        logger.info(f"[EMIT_MODIFY_EVENT] Queued patch {patch_id}")

        return {
            "status": "queued",
            "patch_id": patch_id,
            "field_patch_count": len(field_patches),
            "message": f"Created modify event patch with {len(field_patches)} changes",
        }

    except Exception as e:
        logger.error(f"[EMIT_MODIFY_EVENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
        }


def _find_event_by_id(week_snapshot: Dict[str, Any], event_id: str) -> Optional[Dict[str, Any]]:
    """Find event by ID in week snapshot."""
    # Assuming week_snapshot has structure: {"days": [{"events": [...]}]}
    days = week_snapshot.get("days", [])
    for day in days:
        events = day.get("events", [])
        for event in events:
            if event.get("id") == event_id:
                return event
    return None


def _generate_field_patches(original: Dict[str, Any], merged: Dict[str, Any]) -> List[EventFieldPatch]:
    """Generate field patches by diffing original vs merged event."""
    patches = []
    diff = DeepDiff(original, merged, ignore_order=False)

    # Handle value changes
    values_changed = diff.get("values_changed", {})
    for path, change in values_changed.items():
        # Parse path like "root['start_time']" → field = 'start_time'
        field_match = re.search(r"\['([^']+)'\]", path)
        if field_match:
            field = field_match.group(1)
            patches.append(
                EventFieldPatch(
                    op_id=uuid.uuid4().hex,
                    operation="modify_field",
                    field=field,
                    from_value=change["old_value"],
                    to_value=change["new_value"],
                )
            )

    return patches
