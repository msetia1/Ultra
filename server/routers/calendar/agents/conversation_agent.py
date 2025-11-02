"""Main conversation agent - routes user intent to specialized agents."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent
from .add_event_agent import run_add_event_agent
from .remove_event_agent import run_remove_event_agent
from .modify_event_agent import run_modify_event_agent
from .move_event_agent import run_move_event_agent

logger = logging.getLogger(__name__)


def create_calendar_conversation_agent(
    week_snapshot: Dict[str, Any],
    conversation_history: str = "",
) -> Agent:
    """Create Calendar Conversation Agent that routes to specialized agents.

    Args:
        week_snapshot: Complete week data with events
        conversation_history: Recent conversation turns

    Returns:
        Agent configured as calendar assistant with specialized tools
    """
    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    instructions = f"""You are a Calendar Assistant helping users manage their weekly schedule through natural conversation.

CURRENT DATE: {current_date}

WEEK SNAPSHOT (all events):
{json.dumps(week_snapshot, indent=2)}

RECENT CONVERSATION:
{conversation_history or "(no prior conversation)"}

YOUR CAPABILITIES:
You have 4 specialized tools for calendar operations:

1. **run_add_event_agent** - For adding new events
   Examples: "Add a meeting tomorrow at 2pm", "Schedule dentist appointment Friday"

2. **run_remove_event_agent** - For deleting events
   Examples: "Cancel Monday's 3pm meeting", "Remove all events on Tuesday"

3. **run_modify_event_agent** - For editing event details
   Examples: "Change the meeting title to 'Budget Review'", "Extend lunch by 30 minutes"

4. **run_move_event_agent** - For relocating events
   Examples: "Move Tuesday's meeting to Wednesday", "Reschedule to 4pm"

ROUTING STRATEGY:
- Classify user intent based on operation type (add/remove/modify/move)
- Call the appropriate specialized tool with the user's request
- For complex requests, break down into multiple tool calls
- Use reasonable defaults (1 hour duration, infer times from context)

CONVERSATION FLOW:
1. Review conversation history - NEVER re-ask for information already provided
2. Use reasonable defaults and take action quickly
3. After tool execution, describe changes and ask user to review the preview
4. Be concise and helpful

IMPORTANT:
- Tools handle their own context automatically (don't duplicate data)
- Tools emit patches that are previewed before persistence
- Multiple operations can be done in sequence"""

    return Agent(
        name="CalendarConversationAgent",
        instructions=instructions,
        model="google/gemini-2.5-flash",
        tools=[
            run_add_event_agent,
            run_remove_event_agent,
            run_modify_event_agent,
            run_move_event_agent,
        ],
    )
