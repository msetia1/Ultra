"""Add event agent - creates new calendar events."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..services.openrouter_client import get_openrouter_client
from ..tools import emit_add_event_patch

logger = logging.getLogger(__name__)


# Tool definition for function calling
ADD_EVENT_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_add_event_patch",
        "description": "Create a new calendar event. Call this function once you have all the required information.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title or name",
                },
                "date": {
                    "type": "string",
                    "description": "Scheduled date in YYYY-MM-DD format",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in HH:MM format (24-hour)",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in HH:MM format (24-hour)",
                },
                "description": {
                    "type": "string",
                    "description": "Optional event description or notes",
                    "default": "",
                },
            },
            "required": ["title", "date", "start_time", "end_time"],
        },
    },
}


async def run_add_event_agent(
    context: Dict[str, Any],
    user_intent: str,
) -> Dict[str, Any]:
    """Run the add event specialized agent.

    Args:
        context: Shared calendar context with week_snapshot, event_locators, etc.
        user_intent: User's intent extracted by conversation agent

    Returns:
        Dict with status, patch_count, and agent_response
    """
    try:
        logger.info(f"[ADD_EVENT_AGENT] Processing: {user_intent[:100]}")

        # Get current date for context
        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        week_snapshot = context.get("week_snapshot", {})

        # Build agent prompt
        system_prompt = f"""You are a specialized Calendar Add Event Agent. Your job is to help users add new events to their weekly calendar.

CURRENT DATE: {current_date}

WEEK SNAPSHOT:
{json.dumps(week_snapshot, indent=2)}

YOUR TASK:
1. Parse the user's intent to extract event details
2. Apply reasonable defaults for missing information:
   - Duration: 1 hour if not specified
   - Start time: Infer from context ("morning" = 9am, "afternoon" = 2pm, "evening" = 6pm)
   - Title: Extract from message or use "New Event"
   - Description: Empty string if not provided
3. Call emit_add_event_patch with complete event data
4. Confirm event creation to user

IMPORTANT:
- Use 24-hour time format (14:00 not 2pm)
- Validate date is a valid date string
- Always call emit_add_event_patch exactly once per event
- If multiple events requested, call tool multiple times"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_intent},
        ]

        # Call OpenRouter with function calling
        client = get_openrouter_client()
        response = await client.chat_completion(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",
            tools=[ADD_EVENT_TOOL],
            tool_choice="auto",
        )

        # Process tool calls
        message = response.choices[0].message
        patches_created = 0

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "emit_add_event_patch":
                    args = json.loads(tool_call.function.arguments)
                    result = emit_add_event_patch(context, **args)
                    if result["status"] == "queued":
                        patches_created += 1
                        logger.info(f"[ADD_EVENT_AGENT] Created patch {result['patch_id']}")

        # Get final response text
        final_response = message.content or f"Created {patches_created} event(s)"

        logger.info(f"[ADD_EVENT_AGENT] Completed with {patches_created} patches")

        return {
            "status": "completed",
            "patch_count": patches_created,
            "agent_response": final_response,
        }

    except Exception as e:
        logger.error(f"[ADD_EVENT_AGENT] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "patch_count": 0,
            "agent_response": f"Failed to add event: {str(e)}",
        }
