"""Remove event agent - deletes calendar events."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..services.openrouter_client import get_openrouter_client
from ..tools import emit_remove_event_patch

logger = logging.getLogger(__name__)


REMOVE_EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_remove_event_patch",
        "description": "Remove a calendar event. Call this function for each event to delete.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "UUID of the event to remove",
                },
                "date": {
                    "type": "string",
                    "description": "Scheduled date of the event in YYYY-MM-DD format",
                },
            },
            "required": ["event_id", "date"],
        },
    },
}


async def run_remove_event_agent(
    context: Dict[str, Any],
    user_intent: str,
) -> Dict[str, Any]:
    """Run the remove event specialized agent.

    Args:
        context: Shared calendar context
        user_intent: User's intent extracted by conversation agent

    Returns:
        Dict with status, patch_count, and agent_response
    """
    try:
        logger.info(f"[REMOVE_EVENT_AGENT] Processing: {user_intent[:100]}")

        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        week_snapshot = context.get("week_snapshot", {})
        event_locators = context.get("event_locators", {})

        system_prompt = f"""You are a specialized Calendar Remove Event Agent. Your job is to help users delete events from their weekly calendar.

CURRENT DATE: {current_date}

WEEK SNAPSHOT:
{json.dumps(week_snapshot, indent=2)}

EVENT LOCATORS (event_id -> date):
{json.dumps(event_locators, indent=2)}

YOUR TASK:
1. Identify which event(s) the user wants to remove
2. Find the event_id and date from the week snapshot
3. Call emit_remove_event_patch for each event to delete
4. Confirm deletion to user

IMPORTANT:
- Match events by title, time, or date based on user description
- If multiple events match, ask for clarification or remove all if user said "all"
- Use exact event_id from the snapshot"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_intent},
        ]

        client = get_openrouter_client()
        response = await client.chat_completion(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",
            tools=[REMOVE_EVENT_TOOL],
            tool_choice="auto",
        )

        message = response.choices[0].message
        patches_created = 0

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "emit_remove_event_patch":
                    args = json.loads(tool_call.function.arguments)
                    result = emit_remove_event_patch(context, **args)
                    if result["status"] == "queued":
                        patches_created += 1
                        logger.info(f"[REMOVE_EVENT_AGENT] Created patch {result['patch_id']}")

        final_response = message.content or f"Removed {patches_created} event(s)"

        logger.info(f"[REMOVE_EVENT_AGENT] Completed with {patches_created} patches")

        return {
            "status": "completed",
            "patch_count": patches_created,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"[REMOVE_EVENT_AGENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "patch_count": 0,
            "agent_response": f"Failed to remove event: {str(e)}",
        }
