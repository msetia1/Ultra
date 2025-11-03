"""Move event agent - relocates events to different dates."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent, function_tool, RunContextWrapper
from ..tools import emit_move_event_patch
from ..models import CalendarContext

logger = logging.getLogger(__name__)


def create_move_event_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, Any],
    conversation_history: str = "",
) -> Agent:
    """Create Move Event Agent instance.

    Args:
        week_snapshot: Complete week data with events
        event_locators: event_id -> EventDayLocator mapping
        conversation_history: Recent conversation turns for context

    Returns:
        Agent configured for moving calendar events
    """
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    instructions = f"""You are a specialized Calendar Move Event Agent. Your job is to help users move events to different dates/times.

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

MOVE PARAMETERS FORMAT (CRITICAL - READ CAREFULLY):
═══════════════════════════════════════════════════════════

When calling emit_move_event_patch, provide exact parameters with NO placeholders.

MOVE BEHAVIOR:
- Moving only changes the scheduled_date by default, times stay the same
- If user specifies a new time, include adjust_start_time and adjust_end_time
- Duration is preserved unless explicitly changed

✅ VALID FORMAT - Exact parameters:

Example 1 - Move to different date (keep same time):
from_date="2025-03-04"
to_date="2025-03-06"
adjust_start_time=None
adjust_end_time=None

Example 2 - Move to different date AND time:
from_date="2025-03-03"
to_date="2025-03-04"
adjust_start_time="10:00"
adjust_end_time="11:00"

Example 3 - Move and extend duration:
from_date="2025-03-05"
to_date="2025-03-06"
adjust_start_time="14:00"
adjust_end_time="16:00"

❌ INVALID - Do NOT use placeholders:
from_date="<current-date>"  ← NEVER DO THIS
to_date="<target-date>"

BEST PRACTICES:
- Use YYYY-MM-DD format for dates
- Use 24-hour format for times (e.g., "14:00" not "2pm")
- Calculate duration preservation: if original was 1hr, new end_time = start_time + 1hr
- All parameters are required (use None for optional adjust times)

TOOL CALL EXAMPLES:

User: "Move Tuesday's meeting to Thursday"
→ Find event on Tuesday (2025-03-04)
→ Call: emit_move_event_patch(
    event_id="abc-123",
    from_date="2025-03-04",
    to_date="2025-03-06",
    adjust_start_time=None,
    adjust_end_time=None
  )

User: "Reschedule the standup to tomorrow at 10am"
→ Find standup event (currently at 09:00-10:00)
→ Call: emit_move_event_patch(
    event_id="def-456",
    from_date="2025-03-03",
    to_date="2025-03-04",
    adjust_start_time="10:00",
    adjust_end_time="11:00"
  )

User: "Move Friday's workout to Saturday morning"
→ Find workout on Friday
→ Call: emit_move_event_patch(
    event_id="ghi-789",
    from_date="2025-03-08",
    to_date="2025-03-09",
    adjust_start_time="09:00",
    adjust_end_time="10:00"
  )

CONVERSATION HISTORY:
{conversation_history}"""

    return Agent(
        name="MoveEventAgent",
        instructions=instructions,
        model="openai/gpt-4.1",
        tools=[emit_move_event_patch],
    )


@function_tool
async def run_move_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> str:
    """Run the move event specialized agent (callable as a tool).

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        user_intent: User's intent extracted by conversation agent

    Returns:
        Agent response confirming event move
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
    logger.info(f"[MOVE_EVENT_AGENT] Processing: {user_intent[:100]}")

    try:
        # Extract model_provider from context
        model_provider = context.agent_outputs.get("model_provider")
        logger.info(f"[MOVE_EVENT_AGENT] Retrieved model_provider from context: {model_provider is not None}")

        # Create agent with current week context
        agent = create_move_event_agent(
            week_snapshot=context.week_snapshot,
            event_locators=context.event_locators,
            conversation_history=context.conversation_history or "",
        )

        # Run agent to completion with model provider
        result = await Runner.run(
            starting_agent=agent,
            input=user_intent,
            context=wrapper,
            run_config=RunConfig(model_provider=model_provider) if model_provider else None,
        )

        logger.info(f"[MOVE_EVENT_AGENT] Completed")
        return str(result.final_output) if result.final_output else "Event moved successfully"

    except Exception as e:
        logger.error(f"[MOVE_EVENT_AGENT] Failed: {e}", exc_info=True)
        return f"Failed to move event: {str(e)}"
