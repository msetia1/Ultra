"""Add event agent - creates new calendar events."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent, function_tool, RunContextWrapper
from ..tools import emit_add_event_patch
from ..models import CalendarContext

logger = logging.getLogger(__name__)


def create_add_event_agent(
    week_snapshot: Dict[str, Any],
    conversation_history: str = "",
) -> Agent:
    """Create Add Event Agent instance.

    Args:
        week_snapshot: Complete week data with events
        conversation_history: Recent conversation turns for context

    Returns:
        Agent configured for adding calendar events
    """
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    instructions = f"""You are a specialized Calendar Add Event Agent. Your job is to help users add new events to their weekly calendar.

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
- If multiple events requested, call tool multiple times

CONVERSATION HISTORY:
{conversation_history}"""

    return Agent(
        name="AddEventAgent",
        instructions=instructions,
        model="google/gemini-2.5-flash",
        tools=[emit_add_event_patch],  # Python function, not JSON schema
    )


@function_tool
async def run_add_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> str:
    """Run the add event specialized agent (callable as a tool).

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        user_intent: User's intent extracted by conversation agent

    Returns:
        Agent response confirming event creation
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
    logger.info(f"[ADD_EVENT_AGENT] Processing: {user_intent[:100]}")

    try:
        # Extract model_provider from context
        model_provider = context.agent_outputs.get("model_provider")
        logger.info(f"[ADD_EVENT_AGENT] Retrieved model_provider from context: {model_provider is not None}")

        # Create agent with current week context
        agent = create_add_event_agent(
            week_snapshot=context.week_snapshot,
            conversation_history=context.conversation_history or "",
        )

        # Run agent to completion with model provider
        result = await Runner.run(
            starting_agent=agent,
            input=user_intent,
            context=wrapper,  # Pass wrapped context for tool calls
            run_config=RunConfig(model_provider=model_provider) if model_provider else None,
        )

        logger.info(f"[ADD_EVENT_AGENT] Completed")
        return str(result.final_output) if result.final_output else "Event added successfully"

    except Exception as e:
        logger.error(f"[ADD_EVENT_AGENT] Failed: {e}", exc_info=True)
        return f"Failed to add event: {str(e)}"
