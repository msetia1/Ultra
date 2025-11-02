"""Modify event agent - updates event fields using Morph."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..services.openrouter_client import get_openrouter_client
from ..tools import emit_modify_event_patch

logger = logging.getLogger(__name__)


MODIFY_EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_modify_event_patch",
        "description": "Modify fields of an existing calendar event using Morph API for precise edits.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "UUID of the event to modify",
                },
                "date": {
                    "type": "string",
                    "description": "Scheduled date of the event in YYYY-MM-DD format",
                },
                "instruction": {
                    "type": "string",
                    "description": "First-person description of the change (e.g., 'I am changing the meeting time from 2pm to 3pm')",
                },
                "lazy_edit": {
                    "type": "object",
                    "description": "Minimal JSON object with only the fields being changed (e.g., {\"start_time\": \"15:00\"})",
                },
            },
            "required": ["event_id", "date", "instruction", "lazy_edit"],
        },
    },
}


async def run_modify_event_agent(
    context: Dict[str, Any],
    user_intent: str,
) -> Dict[str, Any]:
    """Run the modify event specialized agent.

    Args:
        context: Shared calendar context
        user_intent: User's intent extracted by conversation agent

    Returns:
        Dict with status, patch_count, and agent_response
    """
    try:
        logger.info(f"[MODIFY_EVENT_AGENT] Processing: {user_intent[:100]}")

        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        week_snapshot = context.get("week_snapshot", {})

        system_prompt = f"""You are a specialized Calendar Modify Event Agent. Your job is to help users modify event details.

CURRENT DATE: {current_date}

WEEK SNAPSHOT:
{json.dumps(week_snapshot, indent=2)}

YOUR TASK:
1. Identify which event the user wants to modify
2. Determine what fields need to change (title, description, start_time, end_time)
3. Create a first-person instruction describing the change
4. Build a lazy_edit object with only the changed fields
5. Call emit_modify_event_patch with the Morph-formatted data

IMPORTANT:
- Use 24-hour time format for times (e.g., "15:00" not "3pm")
- Only include changed fields in lazy_edit
- Instruction should be descriptive (e.g., "I'm extending the meeting by 30 minutes")
- If modifying duration, update both start_time and end_time

EXAMPLES:
- User: "Change the 2pm meeting to 3pm"
  instruction: "I'm moving the meeting start time from 14:00 to 15:00"
  lazy_edit: {"start_time": "15:00", "end_time": "16:00"}

- User: "Rename the standup to 'Daily Sync'"
  instruction: "I'm renaming the event from 'Morning Standup' to 'Daily Sync'"
  lazy_edit: {"title": "Daily Sync"}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_intent},
        ]

        client = get_openrouter_client()
        response = await client.chat_completion(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",
            tools=[MODIFY_EVENT_TOOL],
            tool_choice="auto",
        )

        message = response.choices[0].message
        patches_created = 0

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "emit_modify_event_patch":
                    args = json.loads(tool_call.function.arguments)
                    result = await emit_modify_event_patch(context, **args)
                    if result["status"] == "queued":
                        patches_created += 1
                        logger.info(f"[MODIFY_EVENT_AGENT] Created patch {result['patch_id']}")

        final_response = message.content or f"Modified {patches_created} event(s)"

        logger.info(f"[MODIFY_EVENT_AGENT] Completed with {patches_created} patches")

        return {
            "status": "completed",
            "patch_count": patches_created,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"[MODIFY_EVENT_AGENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "patch_count": 0,
            "agent_response": f"Failed to modify event: {str(e)}",
        }
