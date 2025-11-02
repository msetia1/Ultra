"""Main conversation agent - routes user intent to specialized agents."""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from ..services.openrouter_client import get_openrouter_client
from .add_event_agent import run_add_event_agent
from .remove_event_agent import run_remove_event_agent
from .modify_event_agent import run_modify_event_agent
from .move_event_agent import run_move_event_agent

logger = logging.getLogger(__name__)


# Tool definitions for calling specialized agents
SPECIALIZED_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_add_event_agent",
            "description": "Create new calendar events. Use when user wants to add/create/schedule new events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_intent": {
                        "type": "string",
                        "description": "User's request with all context about what event(s) to add",
                    },
                },
                "required": ["user_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_remove_event_agent",
            "description": "Delete calendar events. Use when user wants to remove/delete/cancel events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_intent": {
                        "type": "string",
                        "description": "User's request specifying which event(s) to remove",
                    },
                },
                "required": ["user_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_modify_event_agent",
            "description": "Modify event details (title, description, time, duration). Use when user wants to change/update/edit event content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_intent": {
                        "type": "string",
                        "description": "User's request specifying what to change about the event",
                    },
                },
                "required": ["user_intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_move_event_agent",
            "description": "Move events to different dates/times. Use when user wants to reschedule/move/relocate events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_intent": {
                        "type": "string",
                        "description": "User's request specifying where to move the event",
                    },
                },
                "required": ["user_intent"],
            },
        },
    },
]


async def run_conversation_agent(
    context: Dict[str, Any],
    user_message: str,
) -> Dict[str, str]:
    """Run the main conversation agent that routes to specialized agents.

    Args:
        context: Shared calendar context with week_snapshot, conversation_history, etc.
        user_message: User's natural language message

    Returns:
        Dict with final_message and status
    """
    try:
        logger.info(f"[CONVERSATION_AGENT] Processing: {user_message[:100]}")

        # Build system prompt
        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        week_snapshot = context.get("week_snapshot", {})
        conversation_history = context.get("conversation_history", "")

        system_prompt = f"""You are a Calendar Assistant helping users manage their weekly schedule through natural conversation.

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

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Call OpenRouter with function calling
        client = get_openrouter_client()
        response = await client.chat_completion(
            messages=messages,
            model="anthropic/claude-3.5-sonnet",
            tools=SPECIALIZED_AGENT_TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        tool_responses = []

        # Execute tool calls (specialized agents)
        if message.tool_calls:
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                logger.info(f"[CONVERSATION_AGENT] Calling {func_name}")

                # Route to appropriate specialized agent
                if func_name == "run_add_event_agent":
                    result = await run_add_event_agent(context, args["user_intent"])
                elif func_name == "run_remove_event_agent":
                    result = await run_remove_event_agent(context, args["user_intent"])
                elif func_name == "run_modify_event_agent":
                    result = await run_modify_event_agent(context, args["user_intent"])
                elif func_name == "run_move_event_agent":
                    result = await run_move_event_agent(context, args["user_intent"])
                else:
                    result = {"status": "error", "agent_response": f"Unknown tool: {func_name}"}

                tool_responses.append(result)
                logger.info(f"[CONVERSATION_AGENT] {func_name} result: {result['status']}, patches: {result.get('patch_count', 0)}")

        # Build final response
        final_message = message.content or "I've processed your request."

        # If we have tool responses, incorporate them
        if tool_responses:
            total_patches = sum(r.get("patch_count", 0) for r in tool_responses)
            if total_patches > 0:
                final_message += f"\n\nI've created {total_patches} proposed change(s) for you to review."

        logger.info(f"[CONVERSATION_AGENT] Completed")

        return {
            "final_message": final_message,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"[CONVERSATION_AGENT] Failed: {e}", exc_info=True)
        return {
            "final_message": f"Sorry, I encountered an error: {str(e)}",
            "status": "error",
        }
