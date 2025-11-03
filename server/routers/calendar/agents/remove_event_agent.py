"""Remove event agent - deletes calendar events."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent, function_tool, RunContextWrapper
from ..tools import emit_remove_event_patch
from ..models import CalendarContext

logger = logging.getLogger(__name__)


def create_remove_event_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, Any],
    conversation_history: str = "",
) -> Agent:
    """Create Remove Event Agent instance.

    Args:
        week_snapshot: Complete week data with events
        event_locators: event_id -> EventDayLocator mapping
        conversation_history: Recent conversation turns for context

    Returns:
        Agent configured for removing calendar events
    """
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    instructions = f"""You are a specialized Calendar Remove Event Agent. Your job is to help users delete events from their weekly calendar.

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
- Use exact event_id from the snapshot

CONVERSATION HISTORY:
{conversation_history}"""

    return Agent(
        name="RemoveEventAgent",
        instructions=instructions,
        model="openai/gpt-4.1",
        tools=[emit_remove_event_patch],
    )


@function_tool
async def run_remove_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> str:
    """Run the remove event specialized agent (callable as a tool).

    Args:
        wrapper: RunContextWrapper containing CalendarContext
        user_intent: User's intent extracted by conversation agent

    Returns:
        Agent response confirming event removal
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
    logger.info(f"[REMOVE_EVENT_AGENT] Processing: {user_intent[:100]}")

    try:
        # Extract model_provider from context
        model_provider = context.agent_outputs.get("model_provider")
        logger.info(f"[REMOVE_EVENT_AGENT] Retrieved model_provider from context: {model_provider is not None}")

        # Create agent with current week context
        agent = create_remove_event_agent(
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

        logger.info(f"[REMOVE_EVENT_AGENT] Completed")
        return str(result.final_output) if result.final_output else "Event removed successfully"

    except Exception as e:
        logger.error(f"[REMOVE_EVENT_AGENT] Failed: {e}", exc_info=True)
        return f"Failed to remove event: {str(e)}"
