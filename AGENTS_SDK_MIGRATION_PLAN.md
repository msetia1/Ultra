# Calendar System: OpenAI Agents SDK Migration Plan

**Project:** YC-Agent-Jam Calendar Chat System
**Goal:** Migrate from direct OpenRouter API calls to OpenAI Agents SDK
**Reference:** TrainWithAI Plan Editor V2 (`/train-with-ai-data/app/routers/training_plans_agents/plan_editor_v2/`)
**Status:** Ready to implement

---

## Table of Contents

1. [Migration Overview](#1-migration-overview)
2. [Architecture Comparison](#2-architecture-comparison)
3. [Dependencies & Setup](#3-dependencies--setup)
4. [Phase 1: Context Models](#phase-1-context-models)
5. [Phase 2: Tool Functions](#phase-2-tool-functions)
6. [Phase 3: Specialized Agents](#phase-3-specialized-agents)
7. [Phase 4: Conversation Agent](#phase-4-conversation-agent)
8. [Phase 5: Router Implementation](#phase-5-router-implementation)
9. [Phase 6: OpenRouter Provider](#phase-6-openrouter-provider)
10. [Testing Strategy](#testing-strategy)
11. [Migration Checklist](#migration-checklist)

---

## 1. Migration Overview

### Why Migrate?

**Current Issues:**
- ❌ No real-time SSE streaming during agent execution
- ❌ Manual tool execution handling
- ❌ No built-in context management
- ❌ Harder to debug agent flows

**Benefits of Agents SDK:**
- ✅ Real-time SSE streaming out of the box
- ✅ Automatic tool execution and handoffs
- ✅ Built-in context passing with RunContextWrapper
- ✅ LangSmith tracing integration
- ✅ Proven pattern from Plan Editor V2

### Migration Strategy

**Approach:** Incremental migration, one component at a time
**Timeline:** ~8-12 hours total
**Risk Level:** Medium (well-tested pattern exists)

---

## 2. Architecture Comparison

### Current Architecture (Direct API)

```python
# Conversation Agent
async def run_conversation_agent(context: Dict, user_message: str):
    client = get_openrouter_client()
    response = await client.chat_completion(
        messages=[...],
        tools=[TOOL_SCHEMA],  # JSON schema
        tool_choice="auto"
    )

    # Manual tool execution
    if response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            # Manually route and execute
            if tool_call.function.name == "run_add_event_agent":
                result = await run_add_event_agent(...)
```

### Target Architecture (Agents SDK)

```python
# Conversation Agent
from agents import Agent, function_tool, RunContextWrapper, Runner

@function_tool
async def run_add_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str
) -> Dict[str, Any]:
    context = _resolve_context(wrapper)
    agent = create_add_event_agent(...)
    result = await Runner.run(
        starting_agent=agent,
        input=user_intent,
        context=wrapper,
        run_config=run_config
    )
    return {"status": "completed", ...}

def create_conversation_agent(...) -> Agent:
    return Agent(
        name="CalendarConversationAgent",
        instructions="...",
        model="anthropic/claude-3.5-sonnet",
        tools=[
            run_add_event_agent,  # Python function, not JSON schema
            run_remove_event_agent,
            run_modify_event_agent,
            run_move_event_agent,
        ]
    )
```

---

## 3. Dependencies & Setup

### Install Agents SDK

```bash
# From YC-Agent-Jam directory
cd server
pip install agents langsmith openai deepdiff
```

### Environment Variables

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
LANGSMITH_API_KEY=...  # Optional for tracing
LANGCHAIN_TRACING_V2=true  # Optional
LANGSMITH_PROJECT=calendar-chat  # Optional
```

### Verify Installation

```python
# test_agents_sdk.py
from agents import Agent, function_tool

@function_tool
def test_tool(message: str) -> str:
    return f"Received: {message}"

agent = Agent(
    name="TestAgent",
    instructions="You are a test agent.",
    model="gpt-4o",
    tools=[test_tool]
)

print("✓ Agents SDK installed correctly")
```

---

## Phase 1: Context Models

### Goal: Create proper context structure with RunContextWrapper support

### File: `server/routers/calendar/models/context.py`

**Current:**
```python
class CalendarContext(BaseModel):
    week_id: str
    user_id: str
    week_snapshot: dict[str, Any]
    event_locators: dict[str, dict]
    conversation_history: Optional[str] = None
    agent_outputs: dict[str, Any] = {}
```

**Target (based on Plan Editor V2):**
```python
"""Context models for calendar agents."""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class CalendarContext(BaseModel):
    """Shared context for calendar agents."""

    # Core data
    week_id: str
    user_id: str
    week_snapshot: dict[str, Any]
    event_locators: dict[str, Any]  # event_id -> EventDayLocator dict

    # Conversation context
    conversation_history: Optional[str] = None

    # Shared state for patches and SSE events
    agent_outputs: dict[str, Any] = {}

    # Allow arbitrary types for compatibility with RunContextWrapper
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        """Initialize with default agent_outputs structure."""
        super().__init__(**data)
        self.agent_outputs.setdefault("proposed_calendar_patches", [])
        self.agent_outputs.setdefault("immediate_sse_events", [])
        self.agent_outputs.setdefault("patch_metadata", {})
```

**Changes:**
1. Add `model_config` for arbitrary types
2. Initialize `agent_outputs` with default keys
3. Match Plan Editor V2 structure

**Testing:**
```python
# Test context creation
context = CalendarContext(
    week_id="2025-W09",
    user_id="test-user",
    week_snapshot={"days": []},
    event_locators={}
)

assert "proposed_calendar_patches" in context.agent_outputs
assert "immediate_sse_events" in context.agent_outputs
```

---

## Phase 2: Tool Functions

### Goal: Convert emit tools from plain functions to @function_tool decorated functions

### Pattern (from Plan Editor V2)

**Reference:** `plan_editor_v2/tools/emit_add_session.py`

```python
from agents import function_tool, RunContextWrapper

def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap nested RunContextWrapper objects."""
    context = wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    if not isinstance(context, CalendarContext):
        raise ValueError("Unable to resolve CalendarContext from wrapper")
    return context

@function_tool
async def emit_add_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> dict[str, Any]:
    """Emit a patch to add a new calendar event."""
    context = _resolve_context(wrapper)
    # ... rest of implementation
```

### File 1: `server/routers/calendar/tools/emit_add_event.py`

**Current:**
```python
def emit_add_event_patch(
    context: Dict[str, Any],  # ❌ Plain dict
    title: str,
    ...
) -> Dict[str, Any]:
```

**Target:**
```python
"""Tool for emitting add event patches."""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict
from agents import function_tool, RunContextWrapper

from ..models import (
    CalendarAddEventPatch,
    CalendarEvent,
    EventDayLocator,
    EventInsertionAnchor,
    CalendarContext  # ← Add this import
)

logger = logging.getLogger(__name__)


def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap nested RunContextWrapper objects used by the Agents SDK."""
    context = wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    if not isinstance(context, CalendarContext):
        raise ValueError("Unable to resolve CalendarContext from wrapper")
    return context


@function_tool  # ← Add decorator
async def emit_add_event_patch(  # ← Make async for consistency
    wrapper: RunContextWrapper[CalendarContext],  # ← Change to wrapper
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> Dict[str, Any]:
    """Emit a patch to add a new calendar event.

    Args:
        wrapper: Wrapped calendar context from Agents SDK
        title: Event title
        date: Scheduled date (YYYY-MM-DD)
        start_time: Start time (HH:MM in 24-hour format)
        end_time: End time (HH:MM in 24-hour format)
        description: Optional event description

    Returns:
        Dict with status and patch_id
    """
    try:
        context = _resolve_context(wrapper)  # ← Unwrap context
        logger.info(f"[EMIT_ADD_EVENT] Creating patch for '{title}' on {date}")

        # Create complete event
        event = CalendarEvent(
            title=title,
            description=description,
            date=date,
            start_time=start_time,
            end_time=end_time,
            event_id=None,
        )

        # Create target day locator
        target_day = EventDayLocator(
            scheduled_date=datetime.strptime(date, "%Y-%m-%d").date(),
            anchor=None,
        )

        # Default insertion hint
        insertion_hint = EventInsertionAnchor(
            relation="end",
            event_id=None,
        )

        # Generate patch
        patch_id = str(uuid.uuid4())
        patch = CalendarAddEventPatch(
            op="add_event",
            target_day=target_day,
            complete_event=event,
            insertion_hint=insertion_hint,
            patch_id=patch_id,
        )

        # Add to context proposed patches
        proposed = context.agent_outputs.setdefault("proposed_calendar_patches", [])
        proposed.append(patch.model_dump(mode="json"))

        # Queue SSE event for streaming
        immediate = context.agent_outputs.setdefault("immediate_sse_events", [])
        immediate.append({
            "type": "patch_proposed",
            "patch": patch.model_dump(mode="json"),
        })

        # Store metadata
        context.agent_outputs.setdefault("patch_metadata", {})[patch_id] = {
            "narration": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"[EMIT_ADD_EVENT] Queued patch {patch_id} to SSE queue")

        return {
            "status": "queued",
            "patch_id": patch_id,
            "message": f"Created add event patch for '{title}'",
        }

    except Exception as e:
        logger.error(f"[EMIT_ADD_EVENT] Failed: {e}", exc_info=True)
        raise  # ← Let Agents SDK handle errors
```

**Key Changes:**
1. ✅ Add `@function_tool` decorator
2. ✅ Change parameter from `context: Dict` to `wrapper: RunContextWrapper[CalendarContext]`
3. ✅ Add `_resolve_context()` helper
4. ✅ Unwrap context before use
5. ✅ Make async for consistency
6. ✅ Raise exceptions instead of returning error dicts (SDK handles it)

### File 2: `server/routers/calendar/tools/emit_remove_event.py`

**Apply same pattern:**
```python
from agents import function_tool, RunContextWrapper

def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    # ... same unwrapping logic

@function_tool
async def emit_remove_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    event_id: str,
    date: str,
) -> Dict[str, Any]:
    context = _resolve_context(wrapper)
    # ... rest of implementation stays the same
```

### File 3: `server/routers/calendar/tools/emit_move_event.py`

Same pattern as above.

### File 4: `server/routers/calendar/tools/emit_modify_event.py`

**Additional Fix:** Add missing `Optional` import + apply @function_tool

```python
from typing import Any, Dict, List, Optional  # ← Fix CRITICAL-1
from agents import function_tool, RunContextWrapper

def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    # ... same unwrapping logic

@function_tool
async def emit_modify_event_patch(
    wrapper: RunContextWrapper[CalendarContext],
    event_id: str,
    date: str,
    instruction: str,
    lazy_edit: Dict[str, Any],
) -> Dict[str, Any]:
    context = _resolve_context(wrapper)
    # ... rest stays the same
```

---

## Phase 3: Specialized Agents

### Goal: Convert specialized agents to use Agents SDK

### Pattern (from Plan Editor V2)

**Reference:** `plan_editor_v2/agents/add_session_agent.py`

```python
from agents import Agent

def create_add_session_agent(
    plan_snapshot: Dict[str, Any],
    session_locators: Dict[str, PlanDayLocator],
    emit_tool: Callable,
    current_date: str,
) -> Agent:
    instructions = f"""
You are a specialized agent...

CURRENT DATE: {current_date}

YOUR TASK:
1. Parse user intent
2. Call emit_tool with event data
...
"""

    return Agent(
        name="AddSessionAgent",
        instructions=instructions,
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool]
    )
```

### File 1: `server/routers/calendar/agents/add_event_agent.py`

**Current Structure:**
```python
# Tool definition (JSON schema)
ADD_EVENT_TOOL = {
    "type": "function",
    "function": {...}
}

# Agent function
async def run_add_event_agent(context: Dict, user_intent: str):
    # Build prompt
    # Call OpenRouter
    # Manual tool execution
```

**Target Structure:**
```python
"""Add event agent - creates new calendar events."""

import logging
from datetime import datetime
from typing import Dict, Any
from agents import Agent, function_tool, RunContextWrapper, Runner, RunConfig

from ..models import CalendarContext
from ..tools import emit_add_event_patch

logger = logging.getLogger(__name__)


def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap nested RunContextWrapper objects."""
    context = wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    if not isinstance(context, CalendarContext):
        raise ValueError("Unable to resolve CalendarContext from wrapper")
    return context


def create_add_event_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, Any],
    emit_tool,  # The actual @function_tool decorated function
    current_date: str,
) -> Agent:
    """Create specialized agent for adding calendar events.

    Args:
        week_snapshot: Full week data with events
        event_locators: Event ID to date mapping
        emit_tool: emit_add_event_patch function
        current_date: Current date for context

    Returns:
        Agent configured for adding events
    """

    import json

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

EXAMPLES:
User: "Add a meeting tomorrow at 2pm"
→ Call emit_add_event_patch(title="Meeting", date="2025-03-05", start_time="14:00", end_time="15:00")

User: "Schedule dentist appointment Friday 10am for 30 minutes"
→ Call emit_add_event_patch(title="Dentist Appointment", date="2025-03-08", start_time="10:00", end_time="10:30")
"""

    return Agent(
        name="AddEventAgent",
        instructions=instructions,
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool],  # Pass the decorated function directly
    )


@function_tool  # ← This is the tool that conversation agent calls
async def run_add_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> Dict[str, Any]:
    """Run the add event specialized agent.

    Use this tool when the user wants to create and schedule new events.
    Examples: "Add a meeting tomorrow at 2pm", "Schedule dentist Friday at 10am"

    Args:
        wrapper: Wrapped calendar context
        user_intent: User's intent extracted by conversation agent

    Returns:
        Dict with status, patch_count, and agent_response
    """
    try:
        logger.info(f"[ADD_EVENT_AGENT] Processing: {user_intent[:100]}")

        context = _resolve_context(wrapper)

        # Initialize agent outputs
        context.agent_outputs.setdefault("proposed_calendar_patches", [])
        context.agent_outputs.setdefault("immediate_sse_events", [])

        # Get current date for agent
        current_date = datetime.now().strftime("%Y-%m-%d (%A)")

        # Create specialized agent
        agent = create_add_event_agent(
            week_snapshot=context.week_snapshot,
            event_locators=context.event_locators,
            emit_tool=emit_add_event_patch,  # Pass the @function_tool
            current_date=current_date,
        )

        logger.info("[ADD_EVENT_AGENT] Created agent with tools")

        # Extract model_provider from context (if stored by parent)
        model_provider = context.agent_outputs.get("model_provider")

        run_config = RunConfig(
            workflow_name="calendar_add_event",
            model_provider=model_provider,  # Use shared provider if available
        )

        logger.info("[ADD_EVENT_AGENT] Running agent")

        # Run agent with Agents SDK
        result = await Runner.run(
            starting_agent=agent,
            input=user_intent,
            context=wrapper,  # Pass wrapper through
            run_config=run_config,
        )

        logger.info("[ADD_EVENT_AGENT] Agent run completed")

        # Count patches created
        patches = context.agent_outputs.get("proposed_calendar_patches", [])
        patches_created = len(patches)

        # Get final response
        final_text = str(result.final_output) if result and result.final_output else f"Created {patches_created} event(s)"

        logger.info(f"[ADD_EVENT_AGENT] Completed with {patches_created} patches")

        return {
            "status": "completed",
            "patch_count": patches_created,
            "agent_response": final_text,
        }

    except Exception as e:
        logger.error(f"[ADD_EVENT_AGENT] Failed: {e}", exc_info=True)
        raise  # Let SDK handle error


# Export both for different use cases
__all__ = ["create_add_event_agent", "run_add_event_agent"]
```

**Key Changes:**
1. ✅ Split into two functions:
   - `create_add_event_agent()` - Creates Agent instance
   - `run_add_event_agent()` - @function_tool that runs the agent
2. ✅ Use `Agent` class with `tools=[emit_add_event_patch]`
3. ✅ Use `Runner.run()` instead of manual execution
4. ✅ Pass `RunContextWrapper` through to child agent
5. ✅ Remove manual tool execution logic

### Files 2-4: Apply Same Pattern

**`remove_event_agent.py`:**
```python
def create_remove_event_agent(...) -> Agent:
    return Agent(
        name="RemoveEventAgent",
        instructions="...",
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool]
    )

@function_tool
async def run_remove_event_agent(
    wrapper: RunContextWrapper[CalendarContext],
    user_intent: str,
) -> Dict[str, Any]:
    # Same pattern as add_event_agent
```

**`modify_event_agent.py`:**
```python
def create_modify_event_agent(...) -> Agent:
    return Agent(
        name="ModifyEventAgent",
        instructions="...",
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool]
    )

@function_tool
async def run_modify_event_agent(...):
    # Same pattern
```

**`move_event_agent.py`:**
```python
def create_move_event_agent(...) -> Agent:
    return Agent(
        name="MoveEventAgent",
        instructions="...",
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool]
    )

@function_tool
async def run_move_event_agent(...):
    # Same pattern
```

---

## Phase 4: Conversation Agent

### Goal: Convert main conversation agent to use Agents SDK

### File: `server/routers/calendar/agents/conversation_agent.py`

**Current:**
```python
# Tool definitions as JSON schemas
SPECIALIZED_AGENT_TOOLS = [
    {"type": "function", "function": {...}},
    ...
]

async def run_conversation_agent(context: Dict, user_message: str):
    # Build prompt
    # Call OpenRouter
    # Manual tool routing
```

**Target:**
```python
"""Main conversation agent - routes user intent to specialized agents."""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from agents import Agent, RunContextWrapper

from ..models import CalendarContext, EventDayLocator
from .add_event_agent import run_add_event_agent
from .remove_event_agent import run_remove_event_agent
from .modify_event_agent import run_modify_event_agent
from .move_event_agent import run_move_event_agent

logger = logging.getLogger(__name__)


def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap nested RunContextWrapper objects."""
    context = wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    if not isinstance(context, CalendarContext):
        raise ValueError("Unable to resolve CalendarContext from wrapper")
    return context


def _format_week_snapshot(week_snapshot: Dict[str, Any]) -> str:
    """Format week snapshot for agent context."""
    try:
        return json.dumps(week_snapshot, indent=2, sort_keys=True)
    except Exception:
        return json.dumps({"error": "unable-to-serialize-week-snapshot"}, indent=2)


def _format_locator_summary(event_locators: Dict[str, Any]) -> str:
    """Format event locators for agent context."""
    try:
        return json.dumps(event_locators, indent=2, sort_keys=True)
    except Exception:
        return json.dumps({}, indent=2)


def create_calendar_conversation_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, Any],
    conversation_history: Optional[str] = None,
) -> Agent:
    """Create the main conversation agent that delegates to specialized agents.

    Args:
        week_snapshot: Full week data with all events
        event_locators: Event ID to date mapping
        conversation_history: Recent conversation turns for context

    Returns:
        Agent configured to route calendar operations
    """

    history_section = conversation_history or "(no prior turns provided)"

    # Calculate current date for agent context
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    day_of_week = now.strftime("%A")

    instructions = f"""You are TrainWithAI's Calendar Assistant. You help users manage their weekly schedule through natural conversation.

CURRENT DATE: {current_date} ({day_of_week})

CONTEXT:
- Week Snapshot (all events):
{_format_week_snapshot(week_snapshot)}

- Event Locator Table (event_id -> date):
{_format_locator_summary(event_locators)}

- Recent Conversation (IMPORTANT: Review carefully to avoid re-asking questions):
{history_section}

AVAILABLE OPERATION TOOLS:
You have 4 specialized tools for calendar modifications:

1. **run_add_event_agent** - For adding new events
   - Use when: User wants to create and schedule new events
   - Examples: "Add a meeting tomorrow at 2pm", "Schedule dentist Friday"

2. **run_remove_event_agent** - For deleting events
   - Use when: User wants to remove/cancel events
   - Examples: "Cancel Monday's 3pm meeting", "Remove all events on Tuesday"

3. **run_modify_event_agent** - For editing event details
   - Use when: User wants to change event content (title, description, time, duration)
   - Examples: "Change the meeting title to 'Budget Review'", "Extend lunch by 30 minutes"

4. **run_move_event_agent** - For relocating events
   - Use when: User wants to move events to different dates/times
   - Examples: "Move Tuesday's meeting to Wednesday", "Reschedule to 4pm"

ROUTING GUIDELINES:
- Classify user intent based on operation type (add/remove/modify/move)
- Call the appropriate specialized tool with clear user_intent string
- Multiple operations → call multiple tools sequentially
- Complex requests → break down into separate tool calls

REASONABLE DEFAULTS:
- Meeting without duration → 1 hour
- "Lunch" → 12pm-1pm
- "Morning" → 9am-12pm, "Afternoon" → 1pm-5pm
- Missing day → use context from conversation or infer from "tomorrow", "next week", etc.

CONVERSATION FLOW RULES:
1. Extract ALL facts from the conversation history above before responding
2. NEVER re-ask for information the user already provided in previous turns
3. Use reasonable defaults and take action - user can refine later
4. Limit clarifications to ONE question max, only if truly blocking
5. Acknowledge understanding + take action in same response

EXECUTION PATTERN:
When user requests modifications:
1. Review conversation history for all relevant details
2. Use reasonable defaults for missing parameters
3. If enough info exists, act immediately:
   a) Acknowledge: "I'll add a 1-hour meeting on Friday at 2pm..."
   b) State defaults: "...using 'Team Sync' as the title..."
   c) Call appropriate tool with user_intent
4. After tool resolves, describe proposed changes and ask user to review preview

IMPORTANT:
- Tools handle their own context automatically (don't pass week_snapshot or locators)
- Tools emit patches as previews for user to accept/reject
- Be conversational and helpful
"""

    return Agent(
        name="CalendarConversationAgent",
        instructions=instructions,
        model="anthropic/claude-3.5-sonnet",
        tools=[
            run_add_event_agent,  # ← Python functions, not JSON schemas
            run_remove_event_agent,
            run_modify_event_agent,
            run_move_event_agent,
        ],
    )


# No more standalone run_conversation_agent function
# Agent will be run by router using Runner.run_streamed()
```

**Key Changes:**
1. ✅ Remove `async def run_conversation_agent()` function
2. ✅ Create `create_calendar_conversation_agent()` that returns `Agent`
3. ✅ Use `Agent` class with Python function tools
4. ✅ Remove manual tool routing logic
5. ✅ SDK handles tool execution automatically

---

## Phase 5: Router Implementation

### Goal: Implement SSE streaming with RunContextWrapper

### File: `server/routers/calendar/routers/chat_router.py`

**Reference:** `plan_editor_v2/router/chat_router.py`

**Target Implementation:**
```python
"""SSE streaming chat router for calendar agent."""

import json
import logging
from typing import AsyncGenerator, Set, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from agents import RunConfig, RunContextWrapper, Runner

from integrations.supabase_service import get_supabase
from integrations.auth_service import get_current_user, User  # ← Fix auth
from ..models import CalendarChatRequest, CalendarContext
from ..services import (
    CalendarContextLoader,
    CalendarConversationManager,
)
from ..agents import create_calendar_conversation_agent
from .sse_events import format_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Chat"])


# Import OpenRouter provider (we'll create this in Phase 6)
from ..services.openrouter_provider import OPENROUTER_PROVIDER


def _resolve_context(wrapper: RunContextWrapper[CalendarContext]) -> CalendarContext:
    """Unwrap nested RunContextWrapper objects."""
    context = wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1
    if not isinstance(context, CalendarContext):
        raise ValueError("Unable to resolve CalendarContext from wrapper")
    return context


def _pull_immediate_events(
    context_wrapper: RunContextWrapper[CalendarContext],
    emitted_patch_ids: Set[str],
) -> List[Dict[str, Any]]:
    """Pull and deduplicate immediate events from queue."""
    context = _resolve_context(context_wrapper)
    queue = context.agent_outputs.get("immediate_sse_events", [])
    payloads: List[Dict[str, Any]] = []

    while queue:
        event = queue.pop(0)
        if not isinstance(event, dict):
            continue

        patch_info = event.get("patch")
        patch_id = patch_info.get("patch_id") if isinstance(patch_info, dict) else None

        # Deduplicate by patch_id
        if patch_id and patch_id in emitted_patch_ids:
            continue
        if patch_id:
            emitted_patch_ids.add(patch_id)

        payloads.append(event)

    return payloads


def _serialize_patches(patches: List[Any]) -> List[Dict[str, Any]]:
    """Serialize patches to JSON-compatible dicts."""
    serialized: List[Dict[str, Any]] = []
    for patch in patches:
        if isinstance(patch, dict):
            serialized.append(patch)
        else:
            # Handle Pydantic models
            serialized.append(patch.model_dump(mode="json"))
    return serialized


@router.post("/chat/{week_id}")
async def chat_with_calendar(
    week_id: str,
    request: CalendarChatRequest,
    current_user: User = Depends(get_current_user),  # ✓ Real auth
) -> StreamingResponse:
    """Stream calendar chat responses with real-time patch emission.

    SSE Event Types:
    - patch_proposed: New patch from agent tool (emitted immediately)
    - message_delta: Streaming text response (token by token)
    - final: Complete message + all patches

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        request: Chat request with message and optional conversation_id
        current_user: Authenticated user

    Returns:
        SSE stream of events
    """
    try:
        logger.info(f"[CHAT_ROUTER] Starting chat for week {week_id}, user {current_user.id}")

        # Get database client
        db_client = get_supabase()

        # Initialize conversation manager
        conversation_manager = CalendarConversationManager(db_client)
        conversation = await conversation_manager.get_or_create_conversation(
            week_id=week_id,
            user_id=current_user.id,
            conversation_id=request.conversation_id,
        )

        # Load week context
        context_loader = CalendarContextLoader(db_client)
        calendar_context = await context_loader.load_week_context(
            week_id=week_id,
            user_id=current_user.id,
        )

        # Get conversation history
        history = await conversation_manager.get_conversation_context(
            conversation_id=conversation["id"],
            max_turns=10,
        )

        # Create CalendarContext model
        context = CalendarContext(
            week_id=week_id,
            user_id=current_user.id,
            week_snapshot=calendar_context["week_snapshot"],
            event_locators=calendar_context["event_locators"],
            conversation_history=history,
            agent_outputs={
                "proposed_calendar_patches": [],
                "immediate_sse_events": [],
                "patch_metadata": {},
            }
        )

        # Store model_provider for child agents
        context.agent_outputs["model_provider"] = OPENROUTER_PROVIDER
        logger.info("[CHAT_ROUTER] Stored model_provider in context for child agents")

        # Create conversation agent
        conversation_agent = create_calendar_conversation_agent(
            week_snapshot=context.week_snapshot,
            event_locators=context.event_locators,
            conversation_history=history,
        )

        # Wrap context for Agents SDK
        context_wrapper = RunContextWrapper(context)

        run_config = RunConfig(
            workflow_name="calendar_chat",
            trace_metadata={
                "component": "calendar-chat",
                "week_id": week_id,
                "user_id": current_user.id,
                "conversation_id": conversation["id"],
            },
            group_id=request.conversation_id or week_id,
            model_provider=OPENROUTER_PROVIDER,  # ← Use custom provider
        )

        logger.info("[CHAT_ROUTER] Starting streaming run")

        # Start streaming run
        streaming_run = Runner.run_streamed(
            starting_agent=conversation_agent,
            input=request.message,
            context=context_wrapper,
            run_config=run_config,
        )

        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from agent execution."""
            emitted_patch_ids: Set[str] = set()
            message_chunks: List[str] = []

            # Stream events AS THEY HAPPEN during agent execution
            async for stream_event in streaming_run.stream_events():
                # Pull immediate events (patches emitted by tools)
                immediate_events = _pull_immediate_events(context_wrapper, emitted_patch_ids)
                if immediate_events:
                    logger.info(f"[CHAT_ROUTER] Pulled {len(immediate_events)} immediate events")
                for payload in immediate_events:
                    yield format_sse(payload)

                # Handle message deltas (streaming text)
                event_type = getattr(stream_event, "type", "")
                if event_type == "raw_response_event":
                    delta_event = getattr(stream_event, "data", None)
                    if delta_event is None:
                        continue
                    if getattr(delta_event, "type", None) == "response.output_text.delta":
                        delta_text = getattr(delta_event, "delta", None)
                        if delta_text:
                            message_chunks.append(delta_text)
                            yield format_sse({"type": "message_delta", "delta": delta_text})
                else:
                    # Tool outputs often enqueue immediate events
                    immediate_events_after_tool = _pull_immediate_events(context_wrapper, emitted_patch_ids)
                    if immediate_events_after_tool:
                        logger.info(f"[CHAT_ROUTER] Pulled {len(immediate_events_after_tool)} events after tool")
                    for payload in immediate_events_after_tool:
                        yield format_sse(payload)

            # Flush any remaining immediate events
            final_immediate = _pull_immediate_events(context_wrapper, emitted_patch_ids)
            if final_immediate:
                logger.info(f"[CHAT_ROUTER] Pulled {len(final_immediate)} events during final flush")
            for payload in final_immediate:
                yield format_sse(payload)

            # Get final message and patches
            final_output = streaming_run.final_output
            final_message = str(final_output) if isinstance(final_output, str) else "".join(message_chunks)

            proposed_patches = context.agent_outputs.get("proposed_calendar_patches", [])
            logger.info(f"[CHAT_ROUTER] Stream complete. Found {len(proposed_patches)} proposed patches")

            # Determine intent
            detected_intent = "edit" if proposed_patches else "question"

            # Save conversation turn
            await conversation_manager.add_conversation_turn(
                conversation_id=conversation["id"],
                user_message=request.message,
                agent_response=final_message,
                patches=proposed_patches,
            )

            # Emit final event
            yield format_sse({
                "type": "final",
                "message": final_message,
                "patches": _serialize_patches(proposed_patches),
                "conversation_id": conversation["id"],
            })

            logger.info(f"[CHAT_ROUTER] Stream completed with {len(proposed_patches)} patches")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"[CHAT_ROUTER] Failed to initialize chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Create new file: `server/routers/calendar/routers/sse_events.py`**
```python
"""SSE event formatting utilities."""

import json
from typing import Dict, Any


def format_sse(payload: Dict[str, Any]) -> str:
    """Format payload as SSE event."""
    return f"data: {json.dumps(payload)}\n\n"
```

**Key Changes:**
1. ✅ Use `Runner.run_streamed()` instead of `Runner.run()`
2. ✅ Stream events in real-time with `async for stream_event in streaming_run.stream_events()`
3. ✅ Pull immediate events during streaming (not after completion)
4. ✅ Handle message deltas for token-by-token text streaming
5. ✅ Use `RunContextWrapper` to wrap CalendarContext
6. ✅ Fix auth with real user dependency

---

## Phase 6: OpenRouter Provider

### Goal: Create custom ModelProvider for OpenRouter

### File: `server/routers/calendar/services/openrouter_provider.py` (NEW)

**Reference:** `plan_editor_v2/router/chat_router.py:37-51`

```python
"""OpenRouter model provider for Agents SDK."""

import os
import logging
from typing import Optional
from agents import ModelProvider, OpenAIChatCompletionsModel, Model
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


# Create OpenRouter client for all calendar agent calls
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)


class OpenRouterModelProvider(ModelProvider):
    """Model provider that routes all models through OpenRouter."""

    def get_model(self, model_name: str | None) -> Model:
        """Get model from OpenRouter.

        Args:
            model_name: Model name in OpenRouter format (e.g., "anthropic/claude-3.5-sonnet")

        Returns:
            Model instance configured for OpenRouter
        """
        # Pass model name directly to OpenRouter (handles all prefixes)
        return OpenAIChatCompletionsModel(
            model=model_name or "anthropic/claude-3.5-sonnet",
            openai_client=openrouter_client
        )

    def supports_model(self, model_name: str) -> bool:
        """Check if model is supported.

        OpenRouter handles routing for all models, so always return True.

        Args:
            model_name: Model name to check

        Returns:
            Always True (OpenRouter handles all model routing)
        """
        return True


# Singleton instance
OPENROUTER_PROVIDER = OpenRouterModelProvider()

logger.info("[OPENROUTER_PROVIDER] Initialized with base_url: https://openrouter.ai/api/v1")
```

**Usage in agents:**
```python
from ..services.openrouter_provider import OPENROUTER_PROVIDER

run_config = RunConfig(
    workflow_name="calendar_chat",
    model_provider=OPENROUTER_PROVIDER,  # ← Use custom provider
)
```

**Update `services/__init__.py`:**
```python
from .openrouter_provider import OPENROUTER_PROVIDER, openrouter_client

__all__ = [
    # ... existing exports
    "OPENROUTER_PROVIDER",
    "openrouter_client",
]
```

---

## Testing Strategy

### Unit Tests

**Test File: `server/routers/calendar/tests/test_agents_sdk.py`**
```python
"""Tests for Agents SDK integration."""

import pytest
from agents import RunContextWrapper

from ..models import CalendarContext
from ..tools import emit_add_event_patch


@pytest.mark.asyncio
async def test_emit_add_event_with_wrapper():
    """Test emit_add_event_patch with RunContextWrapper."""
    # Create context
    context = CalendarContext(
        week_id="2025-W09",
        user_id="test-user",
        week_snapshot={"days": []},
        event_locators={},
    )

    # Wrap context
    wrapper = RunContextWrapper(context)

    # Call tool
    result = await emit_add_event_patch(
        wrapper=wrapper,
        title="Test Meeting",
        date="2025-03-01",
        start_time="14:00",
        end_time="15:00",
        description="Test event",
    )

    # Verify
    assert result["status"] == "queued"
    assert "patch_id" in result

    # Check context was updated
    patches = context.agent_outputs["proposed_calendar_patches"]
    assert len(patches) == 1
    assert patches[0]["op"] == "add_event"

    # Check SSE event queued
    events = context.agent_outputs["immediate_sse_events"]
    assert len(events) == 1
    assert events[0]["type"] == "patch_proposed"


@pytest.mark.asyncio
async def test_add_event_agent_creation():
    """Test creating add event agent."""
    from ..agents import create_add_event_agent
    from ..tools import emit_add_event_patch

    agent = create_add_event_agent(
        week_snapshot={"days": []},
        event_locators={},
        emit_tool=emit_add_event_patch,
        current_date="2025-03-01 (Saturday)",
    )

    # Verify agent properties
    assert agent.name == "AddEventAgent"
    assert agent.model == "anthropic/claude-3.5-sonnet"
    assert len(agent.tools) == 1
    assert agent.tools[0] == emit_add_event_patch


@pytest.mark.asyncio
async def test_conversation_agent_creation():
    """Test creating conversation agent."""
    from ..agents import create_calendar_conversation_agent

    agent = create_calendar_conversation_agent(
        week_snapshot={"days": []},
        event_locators={},
        conversation_history="(no prior conversation)",
    )

    # Verify agent properties
    assert agent.name == "CalendarConversationAgent"
    assert len(agent.tools) == 4  # 4 specialized agents
```

### Integration Tests

**Test File: `server/routers/calendar/tests/test_streaming.py`**
```python
"""Tests for SSE streaming."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.asyncio
async def test_chat_router_streams_patches():
    """Test that chat router streams patches in real-time."""
    # Mock dependencies
    with patch("..routers.chat_router.get_current_user") as mock_auth:
        mock_auth.return_value = Mock(id="test-user")

        # Mock DB to return test data
        with patch("..routers.chat_router.get_supabase") as mock_db:
            # Setup mocks...

            # Make request
            response = client.post(
                "/calendar/chat/2025-W09",
                json={"message": "Add meeting tomorrow at 2pm"},
            )

            # Collect SSE events
            events = []
            for line in response.iter_lines():
                if line.startswith(b"data: "):
                    event = json.loads(line[6:])
                    events.append(event)

            # Verify streaming
            patch_events = [e for e in events if e["type"] == "patch_proposed"]
            assert len(patch_events) > 0

            # Verify final event
            final_events = [e for e in events if e["type"] == "final"]
            assert len(final_events) == 1
            assert "patches" in final_events[0]
```

### Manual Testing

**1. Test Real-Time Streaming:**
```bash
# Terminal 1: Start server
cd server
uvicorn main:app --reload

# Terminal 2: Test SSE endpoint
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Add meeting tomorrow at 2pm"}' \
  http://localhost:8000/calendar/chat/2025-W09
```

**Expected Output:**
```
data: {"type":"patch_proposed","patch":{...}}

data: {"type":"message_delta","delta":"I'll"}

data: {"type":"message_delta","delta":" add"}

data: {"type":"message_delta","delta":" a"}

data: {"type":"final","message":"I'll add a meeting tomorrow at 2pm...","patches":[...]}
```

**2. Test with Frontend:**
```typescript
// Frontend test
const eventSource = new EventSource('/api/calendar/chat/2025-W09');

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'patch_proposed') {
    console.log('✓ Patch received in real-time!', data.patch);
  }

  if (data.type === 'message_delta') {
    console.log('✓ Streaming text:', data.delta);
  }

  if (data.type === 'final') {
    console.log('✓ Complete!', data.message);
  }
});
```

---

## Migration Checklist

### Phase 1: Context Models ✓
- [ ] Update `models/context.py` with `model_config`
- [ ] Add default `agent_outputs` initialization
- [ ] Test context creation

### Phase 2: Tool Functions ✓
- [ ] Add `_resolve_context()` to each tool file
- [ ] Add `@function_tool` decorator to `emit_add_event_patch`
- [ ] Add `@function_tool` decorator to `emit_remove_event_patch`
- [ ] Add `@function_tool` decorator to `emit_move_event_patch`
- [ ] Add `@function_tool` decorator to `emit_modify_event_patch`
- [ ] Fix missing `Optional` import in `emit_modify_event.py`
- [ ] Change parameters from `context: Dict` to `wrapper: RunContextWrapper`
- [ ] Test each tool individually

### Phase 3: Specialized Agents ✓
- [ ] Create `create_add_event_agent()` function
- [ ] Convert `run_add_event_agent()` to `@function_tool`
- [ ] Create `create_remove_event_agent()` function
- [ ] Convert `run_remove_event_agent()` to `@function_tool`
- [ ] Create `create_modify_event_agent()` function
- [ ] Convert `run_modify_event_agent()` to `@function_tool`
- [ ] Create `create_move_event_agent()` function
- [ ] Convert `run_move_event_agent()` to `@function_tool`
- [ ] Test agent creation for each type

### Phase 4: Conversation Agent ✓
- [ ] Remove `async def run_conversation_agent()` function
- [ ] Create `create_calendar_conversation_agent()` returning `Agent`
- [ ] Update tools parameter to use Python functions
- [ ] Test conversation agent creation

### Phase 5: Router Implementation ✓
- [ ] Update `chat_router.py` to use `Runner.run_streamed()`
- [ ] Add `_pull_immediate_events()` helper
- [ ] Implement event generator with real-time streaming
- [ ] Create `sse_events.py` for formatting
- [ ] Fix auth to use real user dependency
- [ ] Test SSE streaming end-to-end

### Phase 6: OpenRouter Provider ✓
- [ ] Create `services/openrouter_provider.py`
- [ ] Implement `OpenRouterModelProvider` class
- [ ] Create `OPENROUTER_PROVIDER` singleton
- [ ] Update routers to use provider
- [ ] Update agents to use provider

### Phase 7: Service Updates ✓
- [ ] Fix async/sync in `CalendarPersistenceService`
- [ ] Fix async/sync in `CalendarContextLoader`
- [ ] Fix async/sync in `CalendarConversationManager`
- [ ] Update `load_week_context()` to return dict (not CalendarContext)

### Phase 8: Testing ✓
- [ ] Write unit tests for tools
- [ ] Write unit tests for agents
- [ ] Write integration tests for router
- [ ] Manual test with curl
- [ ] Test with frontend

### Phase 9: Documentation ✓
- [ ] Update README with new architecture
- [ ] Add API documentation
- [ ] Document migration from old approach

---

## Rollback Plan

If migration fails, revert in reverse order:

**1. Immediate Rollback (1 hour):**
```bash
# Revert to last working commit
git checkout <commit-before-migration>
git reset --hard
```

**2. Partial Rollback (keep some changes):**
```bash
# Keep Phase 1-2 (context and tools), revert rest
git checkout HEAD~3 server/routers/calendar/agents/
git checkout HEAD~3 server/routers/calendar/routers/
```

**3. Incremental Fix:**
- Identify failing phase
- Revert just that phase
- Fix issues
- Re-apply

---

## Next Steps

**Recommended Order:**

1. **Day 1 (4 hours):** Phases 1-2 (Context + Tools)
   - Low risk, foundational changes
   - Test thoroughly before proceeding

2. **Day 2 (4 hours):** Phases 3-4 (Agents)
   - Medium complexity
   - Can test agents individually

3. **Day 3 (4 hours):** Phases 5-6 (Router + Provider)
   - Highest complexity
   - End-to-end integration

4. **Day 4 (2 hours):** Testing + Documentation
   - Validate everything works
   - Document new architecture

**Total Estimated Time:** 14-16 hours

---

## Success Criteria

Migration is successful when:

✅ All patches emit in real-time during agent execution (not after)
✅ Message text streams token-by-token
✅ No manual tool routing logic remains
✅ All 4 operations (add/remove/modify/move) work correctly
✅ Conversation history is preserved
✅ Real auth is working (no hardcoded test user)
✅ SSE streaming shows patches immediately when tools execute
✅ LangSmith tracing works (optional)

---

## Troubleshooting

### Issue: "Unable to resolve CalendarContext from wrapper"

**Cause:** Context not properly wrapped or wrong type passed

**Fix:**
```python
# Make sure you're creating RunContextWrapper correctly
context = CalendarContext(...)  # Pydantic model
wrapper = RunContextWrapper(context)  # Wrap it

# Not this:
wrapper = RunContextWrapper({"week_id": "..."})  # ❌ Dict won't work
```

### Issue: "Tool not found"

**Cause:** Tool not properly decorated with `@function_tool`

**Fix:**
```python
# Make sure decorator is applied
@function_tool  # ← Must have this
async def emit_add_event_patch(wrapper, ...):
    pass
```

### Issue: "No patches emitted during streaming"

**Cause:** Not pulling immediate events in event generator

**Fix:**
```python
async for stream_event in streaming_run.stream_events():
    # Pull IMMEDIATELY during streaming
    immediate_events = _pull_immediate_events(context_wrapper, emitted_patch_ids)
    for payload in immediate_events:
        yield format_sse(payload)  # ✓ Real-time
```

### Issue: "Model not found"

**Cause:** OpenRouter provider not configured

**Fix:**
```python
# Make sure OPENROUTER_PROVIDER is used in RunConfig
run_config = RunConfig(
    workflow_name="calendar_chat",
    model_provider=OPENROUTER_PROVIDER,  # ← Must include this
)
```

---

**End of Migration Plan**

This plan provides a complete roadmap to migrate your calendar system to the OpenAI Agents SDK using the proven patterns from Plan Editor V2. Follow the phases in order, test thoroughly at each step, and you'll have a production-ready implementation with real-time SSE streaming.
