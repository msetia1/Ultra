"""Modify event agent - updates event fields using Morph."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent, function_tool, RunContextWrapper
from ..tools import emit_modify_event_patch
from ..models import CalendarContext

logger = logging.getLogger(__name__)


def create_modify_event_agent(
    week_snapshot: Dict[str, Any],
    conversation_history: str = "",
) -> Agent:
    """Create Modify Event Agent instance.

    Args:
        week_snapshot: Complete week data with events
        conversation_history: Recent conversation turns for context

    Returns:
        Agent configured for modifying calendar events
    """
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    instructions = f"""You are a specialized Calendar Modify Event Agent. Your job is to help users modify event details.

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
  lazy_edit: {{"start_time": "15:00", "end_time": "16:00"}}

- User: "Rename the standup to 'Daily Sync'"
  instruction: "I'm renaming the event from 'Morning Standup' to 'Daily Sync'"
  lazy_edit: {{"title": "Daily Sync"}}

CONVERSATION HISTORY:
{conversation_history}"""

    return Agent(
        name="ModifyEventAgent",
        instructions=instructions,
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_modify_event_patch],
    )


@function_tool
async def run_modify_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> str:
    """Run the modify event specialized agent (callable as a tool).

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        user_intent: User's intent extracted by conversation agent

    Returns:
        Agent response confirming event modification
    """
    from agents import Runner, RunConfig

    # Unwrap context
    def _resolve_context(w):
        context = w
        guard = 4
        while hasattr(context, "context") and guard:
            context = getattr(context, "context")
            guard -= 1
        return context

    context = _resolve_context(wrapper)
    logger.info(f"[MODIFY_EVENT_AGENT] Processing: {user_intent[:100]}")

    try:
        # Extract model_provider from context
        model_provider = context.agent_outputs.get("model_provider")
        logger.info(f"[MODIFY_EVENT_AGENT] Retrieved model_provider from context: {model_provider is not None}")

        # Create agent with current week context
        agent = create_modify_event_agent(
            week_snapshot=context.week_snapshot,
            conversation_history=context.conversation_history or "",
        )

        # Run agent to completion (async because emit_modify_event_patch is async)
        result = await Runner.run(
            starting_agent=agent,
            input=user_intent,
            context=wrapper,
            run_config=RunConfig(model_provider=model_provider) if model_provider else None,
        )

        logger.info(f"[MODIFY_EVENT_AGENT] Completed")
        return str(result.final_output) if result.final_output else "Event modified successfully"

    except Exception as e:
        logger.error(f"[MODIFY_EVENT_AGENT] Failed: {e}", exc_info=True)
        return f"Failed to modify event: {str(e)}"
