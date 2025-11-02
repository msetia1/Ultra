"""Move event agent - relocates events to different dates."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..services.openrouter_client import get_openrouter_client
from ..tools import emit_move_event_patch

logger = logging.getLogger(__name__)


MOVE_EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_move_event_patch",
        "description": "Move a calendar event to a different date, optionally adjusting times.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "UUID of the event to move",
                },
                "from_date": {
                    "type": "string",
                    "description": "Current date in YYYY-MM-DD format",
                },
                "to_date": {
                    "type": "string",
                    "description": "New date in YYYY-MM-DD format",
                },
                "adjust_start_time": {
                    "type": "string",
                    "description": "Optional new start time in HH:MM format if also changing time",
                },
                "adjust_end_time": {
                    "type": "string",
                    "description": "Optional new end time in HH:MM format if also changing time",
                },
            },
            "required": ["event_id", "from_date", "to_date"],
        },
    },
}


async def run_move_event_agent(
    context: Dict[str, Any],
    user_intent: str,
) -> Dict[str, Any]:
    """Run the move event specialized agent.

    Args:
        context: Shared calendar context
        user_intent: User's intent extracted by conversation agent

    Returns:
        Dict with status, patch_count, and agent_response
    """
    try:
        logger.info(f"[MOVE_EVENT_AGENT] Processing: {user_intent[:100]}")

        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        week_snapshot = context.get("week_snapshot", {})
        event_locators = context.get("event_locators", {})

        system_prompt = f"""You are a specialized Calendar Move Event Agent. Your job is to help users move events to different dates/times.

CURRENT DATE: {current_date}

WEEK SNAPSHOT:
{json.dumps(week_snapshot, indent=2)}

EVENT LOCATORS (event_id -> date):
{json.dumps(event_locators, indent=2)}

YOUR TASK:
1. Identify which event the user wants to move
2. Determine the target date (and optionally new time)
3. Call emit_move_event_patch with from_date and to_date
4. If user also wants to change time, include adjust_start_time and adjust_end_time

IMPORTANT:
- Moving only changes the date by default, times stay the same
- If user says "move meeting to 3pm tomorrow", include adjust_start_time
- Use 24-hour format for time adjustments
- Validate target date is valid

EXAMPLES:
- User: "Move Tuesday's meeting to Thursday"
  Call with: from_date="2025-03-04", to_date="2025-03-06"

- User: "Reschedule the standup to tomorrow at 10am"
  Call with: from_date="2025-03-03", to_date="2025-03-04", adjust_start_time="10:00", adjust_end_time="11:00" """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_intent},
        ]

        client = get_openrouter_client()
        response = await client.chat_completion(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",
            tools=[MOVE_EVENT_TOOL],
            tool_choice="auto",
        )

        message = response.choices[0].message
        patches_created = 0

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "emit_move_event_patch":
                    args = json.loads(tool_call.function.arguments)
                    result = emit_move_event_patch(context, **args)
                    if result["status"] == "queued":
                        patches_created += 1
                        logger.info(f"[MOVE_EVENT_AGENT] Created patch {result['patch_id']}")

        final_response = message.content or f"Moved {patches_created} event(s)"

        logger.info(f"[MOVE_EVENT_AGENT] Completed with {patches_created} patches")

        return {
            "status": "completed",
            "patch_count": patches_created,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"[MOVE_EVENT_AGENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "patch_count": 0,
            "agent_response": f"Failed to move event: {str(e)}",
        }
