# Calendar Chat Implementation Plan

## Overview

This document outlines the implementation approach for a calendar chat system that enables users to update their weekly calendar by conversing with an LLM agent. The architecture follows the proven **Plan Editor V2** pattern with a single Calendar Editor Agent that delegates to specialized sub-agents for different operations.

**Key Features:**
- Natural language calendar modifications
- Preview-first architecture (changes shown before persistence)
- Real-time SSE streaming for immediate feedback
- Morph-powered lazy edits for event modifications
- Simple event data model (title, description, date, times)

---

## 1. Architecture Overview

### Single Calendar Editor Pattern (Recommended)

Based on your existing Plan Editor V2, use a **single Calendar Editor Agent** with specialized tools for calendar operations.

**Advantages:**
- Proven pattern in your codebase (`plan_editor_v2/`)
- Full week context for conflict detection
- Efficient bulk operations ("cancel all meetings this week")
- Natural fit for preview-first + SSE streaming
- Simpler than multi-agent orchestration

**Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Next.js)                  │
│                                                              │
│  ┌────────────┐  SSE Events   ┌──────────────────────┐     │
│  │  Calendar  │◄──────────────┤  EventSource Client  │     │
│  │  Week View │               │  (SSE Stream)        │     │
│  └────────────┘               └──────────────────────┘     │
│        │                              ▲                     │
│        │ Accept Patches               │ Streaming          │
│        ▼                              │                     │
│  ┌────────────────────────────────────┴──────────────────┐ │
│  │         POST /calendar/accept-patches/{week_id}       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS/JWT
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend (train-with-ai-data)           │
│                                                              │
│  POST /calendar/chat/{week_id} (SSE)                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         CalendarConversationAgent (Main)              │ │
│  │              - Routes user intent                     │ │
│  │              - Maintains conversation context         │ │
│  │              - Delegates to specialized tools         │ │
│  └──────────┬────────────────────────────────────────────┘ │
│             │                                               │
│             │ Invokes Tools (Agent-as-Tool Pattern)        │
│             │                                               │
│  ┌──────────┴──────────────────────────────────────────┐   │
│  │         Specialized Sub-Agents (Tools)              │   │
│  │                                                      │   │
│  │  run_add_event_agent    → emit_add_event_patch     │   │
│  │  run_remove_event_agent → emit_remove_event_patch  │   │
│  │  run_modify_event_agent → emit_modify_event_morph  │   │
│  │  run_move_event_agent   → emit_move_event_patch    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          │ Emit SSE Events                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        SSE Event Queue (immediate_sse_events)       │   │
│  │                                                      │   │
│  │  { type: 'patch_proposed', patch: {...} }          │   │
│  │  { type: 'message_delta', delta: '...' }           │   │
│  │  { type: 'final', message: '...', patches: [...] } │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │   Morph API          │
               │   (via OpenRouter)   │
               │   morph/morph-v3-large│
               └──────────────────────┘
```

**Key Components:**

1. **CalendarConversationAgent**: Main routing agent that classifies user intent and delegates to specialized tools
2. **Specialized Sub-Agents**: `run_add_event_agent`, `run_remove_event_agent`, `run_modify_event_agent`, `run_move_event_agent`
3. **Emission Tools**: Functions that generate patches and queue SSE events
4. **SSE Event Queue**: In-memory queue (`context.agent_outputs['immediate_sse_events']`) for streaming patches
5. **Patch Reconciler**: Deduplicates and validates patches before final emission

---

## 2. OpenRouter Integration

### Setup

OpenRouter provides unified access to multiple LLM providers through a single API endpoint.

**Environment Variables:**
```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
```

**Client Initialization:**
```python
# train-with-ai-data/app/routers/calendar/chat_router.py

from openai import AsyncOpenAI
import os

# Create OpenRouter client for all calendar agent calls
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
```

### Custom Model Provider for Agents SDK

The OpenAI Agents SDK requires a custom `ModelProvider` to route calls through OpenRouter:

```python
from agents import ModelProvider, OpenAIChatCompletionsModel, Model

class OpenRouterModelProvider(ModelProvider):
    """Model provider that routes all models through OpenRouter."""

    def get_model(self, model_name: str | None) -> Model:
        # Pass model name directly to OpenRouter (handles all prefixes)
        return OpenAIChatCompletionsModel(
            model=model_name or "anthropic/claude-3.5-sonnet",
            openai_client=openrouter_client
        )

    def supports_model(self, model_name: str) -> bool:
        # Accept all model names - OpenRouter handles routing
        return True

OPENROUTER_PROVIDER = OpenRouterModelProvider()
```

### Usage in Agents

```python
from agents import Agent, RunConfig, Runner

# Create agent (model name uses OpenRouter format)
calendar_agent = Agent(
    name="CalendarConversationAgent",
    instructions="...",
    model="anthropic/claude-3.5-sonnet",  # OpenRouter format
    tools=[...]
)

# Run with OpenRouter provider
run_config = RunConfig(
    workflow_name='calendar_chat',
    model_provider=OPENROUTER_PROVIDER  # ← Use custom provider
)

result = await Runner.run(
    starting_agent=calendar_agent,
    input=user_message,
    context=context_wrapper,
    run_config=run_config
)
```

### Sharing Provider Across Sub-Agents

Store the model provider in the shared context so sub-agents can use it:

```python
# In main chat endpoint
context.agent_outputs["model_provider"] = OPENROUTER_PROVIDER

# In sub-agent tool
model_provider = context.agent_outputs.get("model_provider")
run_config = RunConfig(
    workflow_name='add_event',
    model_provider=model_provider  # ← Reuse from context
)
```

**Supported Models:**
- `anthropic/claude-3.5-sonnet` (recommended for calendar operations)
- `openai/gpt-4-turbo`
- `google/gemini-pro-1.5`
- See https://openrouter.ai/models for full list

---

## 3. Agent-as-Tool Pattern

### Pattern Overview

The **agent-as-tool** pattern treats specialized agents as tools callable by a parent conversation agent. This enables:
- Clear separation of concerns (one agent per operation type)
- Parallel processing for independent operations
- Focused context for each sub-agent
- Reusable tool definitions

### Main Conversation Agent

**Location:** `train-with-ai-data/app/routers/calendar/agents/conversation_agent.py`

```python
from agents import Agent, function_tool, RunContextWrapper

def create_calendar_conversation_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, EventDayLocator],
    conversation_history: Optional[str] = None,
) -> Agent:
    """
    Create the parent conversation agent that delegates to specialized operation agents.

    Args:
        week_snapshot: Full week data with all events
        event_locators: Mapping of event_id -> EventDayLocator (date + anchor)
        conversation_history: Recent conversation turns for context
    """

    history_section = conversation_history or "(no prior turns provided)"
    current_date = datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.now().strftime("%A")

    instructions = f"""
You are a Calendar Assistant for managing the user's weekly schedule. You help them add, remove, modify, and move calendar events through natural conversation.

CURRENT DATE: {current_date} ({day_of_week})

CONTEXT:
- Week Snapshot (all events):
{json.dumps(week_snapshot, indent=2)}

- Event Locator Table (event_id -> date):
{json.dumps(event_locators, indent=2)}

- Recent Conversation:
{history_section}

AVAILABLE OPERATION TOOLS:
You have 4 specialized tools for calendar modifications:

1. **run_add_event_agent** - For adding new events
   - Use when: User wants to create/schedule new events
   - Examples: "Add a meeting tomorrow at 2pm", "Schedule dentist appointment Friday"

2. **run_remove_event_agent** - For deleting events
   - Use when: User wants to remove/cancel events
   - Examples: "Cancel Monday's 3pm meeting", "Remove all events on Tuesday"

3. **run_modify_event_agent** - For editing event details
   - Use when: User wants to change event content (title, description, time, duration)
   - Examples: "Change the meeting title to 'Budget Review'", "Extend lunch by 30 minutes"

4. **run_move_event_agent** - For relocating events
   - Use when: User wants to move events to different days/times
   - Examples: "Move Tuesday's meeting to Wednesday", "Shift everything back 2 hours"

ROUTING GUIDELINES:
- Classify user intent based on operation type (add/remove/modify/move)
- Call the appropriate specialized tool with clear request_intent string
- Multiple operations → call multiple tools sequentially
- Complex requests → break down into separate tool calls

REASONABLE DEFAULTS:
- Meeting without duration → 1 hour
- "Lunch" → 12pm-1pm
- "Morning" → 9am-12pm, "Afternoon" → 1pm-5pm
- Missing day → use context from conversation or infer from "tomorrow", "next week", etc.

CONVERSATION FLOW:
1. Extract all facts from conversation history before responding
2. NEVER re-ask for information already provided
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
   c) Call appropriate tool with request_intent
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
            run_add_event_agent,
            run_remove_event_agent,
            run_modify_event_agent,
            run_move_event_agent,
        ],
    )
```

### Specialized Sub-Agent Tools

Each operation type has a corresponding tool that spins up a specialized agent:

**Example: Add Event Tool**

```python
# train-with-ai-data/app/routers/calendar/agents/conversation_agent.py

@function_tool
async def run_add_event_agent(
    wrapper: RunContextWrapper[CalendarConversationContext],
    request_intent: str,
) -> Dict[str, Any]:
    """
    Add new events to the calendar.

    Use this tool when the user wants to create and schedule new events.
    Examples: "Add a meeting tomorrow at 2pm", "Schedule dentist Friday at 10am"

    Args:
        request_intent: User's intent extracted by parent agent
    """
    logger.info("[ADD_EVENT_AGENT] Called with intent: '%s'", request_intent[:200])

    context = _resolve_context(wrapper)
    context.agent_outputs.setdefault('proposed_calendar_patches', [])
    context.agent_outputs.setdefault('immediate_sse_events', [])

    current_date = datetime.now().strftime("%Y-%m-%d")

    # Create specialized agent
    agent = create_add_event_agent(
        week_snapshot=context.week_snapshot,
        event_locators=context.event_locators,
        emit_tool=emit_add_event_patch,
        current_date=current_date,
    )

    # Extract model_provider from context (shared across agents)
    model_provider = context.agent_outputs.get("model_provider")

    run_config = RunConfig(
        workflow_name='calendar_add_event',
        model_provider=model_provider
    )

    result = await Runner.run(
        starting_agent=agent,
        input=request_intent,
        context=wrapper,
        run_config=run_config,
    )

    patches = context.agent_outputs.get('proposed_calendar_patches', [])
    logger.info('Add event agent completed with %d patches', len(patches))

    final_text = str(result.final_output) if result and result.final_output else ''

    return {
        'status': 'completed',
        'patch_count': len(patches),
        'agent_response': final_text,
    }
```

**Similar tools for:**
- `run_remove_event_agent`
- `run_modify_event_agent`
- `run_move_event_agent`

### Specialized Agent Implementation

**Example: Add Event Agent**

**Location:** `train-with-ai-data/app/routers/calendar/agents/add_event_agent.py`

```python
from agents import Agent

def create_add_event_agent(
    week_snapshot: Dict[str, Any],
    event_locators: Dict[str, EventDayLocator],
    emit_tool: Callable,
    current_date: str,
) -> Agent:
    """
    Create specialized agent for adding calendar events.

    Args:
        week_snapshot: Full week data
        event_locators: Event ID to date mapping
        emit_tool: Function to emit add_event patches
        current_date: Current date for context
    """

    instructions = f"""
You are a specialized Calendar Add Event Agent. Your job is to help users add new events to their weekly calendar.

CURRENT DATE: {current_date}

WEEK SNAPSHOT:
{json.dumps(week_snapshot, indent=2)}

TOOL AVAILABLE:
- emit_add_event_patch: Creates a new calendar event patch

EVENT STRUCTURE:
- title: str (required) - Event name/title
- description: str (optional) - Event details
- date: str (YYYY-MM-DD) - Scheduled date
- start_time: str (HH:MM) - Start time in 24h format
- end_time: str (HH:MM) - End time in 24h format

DEFAULTS TO USE:
- Duration: 1 hour if not specified
- Start time: Infer from context ("morning" = 9am, "afternoon" = 2pm)
- Title: Extract from user message or use "New Event"
- Description: Empty string if not provided

EXECUTION STEPS:
1. Parse user intent to extract event details
2. Apply reasonable defaults for missing fields
3. Call emit_add_event_patch with complete event data
4. Confirm event creation to user

IMPORTANT:
- Always call emit_add_event_patch exactly once per event
- Use 24-hour time format (14:00 not 2pm)
- Validate date is within current week
- If multiple events requested, call tool multiple times
"""

    return Agent(
        name="AddEventAgent",
        instructions=instructions,
        model="anthropic/claude-3.5-sonnet",
        tools=[emit_tool],
    )
```

---

## 4. Morph Integration for Lazy Edits

### What is Morph?

**Morph** is an AI-powered code editing API that applies "lazy edits" to structured data. Instead of generating full replacements, you provide:
- **Original data** (complete JSON)
- **Instruction** (first-person description of change)
- **Lazy edit** (minimal JSON with only changed fields)

Morph intelligently merges the edit at **10,500+ tokens/sec**.

### Why Use Morph for Calendar Events?

- **Speed**: 10,500+ tok/sec vs. ~3,000 tok/sec for standard LLM generation
- **Precision**: No hallucinations - only applies specified changes
- **Diff Generation**: Automatic field-level diff via DeepDiff
- **Proven Pattern**: Already used successfully in your Plan Editor V2

### Morph API via OpenRouter

**Model:** `morph/morph-v3-large`

**Format:**
```
<instruction>First-person description</instruction>
<code>{original_json}</code>
<update>{lazy_edit}</update>
```

### Implementation: Modify Event Tool

**Location:** `train-with-ai-data/app/routers/calendar/tools/emit_modify_morph.py`

```python
from openai import AsyncOpenAI
import os
import json
import uuid
from deepdiff import DeepDiff
from agents import function_tool, RunContextWrapper

@function_tool
async def emit_modify_event_morph(
    wrapper: RunContextWrapper[CalendarConversationContext],
    event_id: str,
    instruction: str,
    lazy_edit: str,
) -> Dict[str, Any]:
    """
    Apply lazy edit to calendar event via Morph and generate field patches.

    Uses Morph API (OpenRouter: morph/morph-v3-large) to merge lazy edits,
    then diffs to generate EventFieldPatch[] for CalendarModifyEventPatch.

    Args:
        event_id: UUID of event to modify
        instruction: First-person description of change
            Example: "I'm changing the meeting time from 2pm to 3pm"
        lazy_edit: Minimal JSON with only changed fields
            Example: '{"start_time": "15:00", "end_time": "16:00"}'

    Returns:
        Dict with status, patch_id, and field_patch_count
    """
    try:
        context = _resolve_context(wrapper)

        # Get original event from week snapshot
        original_event = _get_event_by_id(context.week_snapshot, event_id)
        if not original_event:
            raise ValueError(f"Event {event_id} not found in week snapshot")

        logger.info("[MODIFY_EVENT_MORPH] Found original event: %s", original_event.get('title'))

        # Create OpenRouter client
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        # Prepare original event JSON
        original_json = json.dumps(original_event, indent=2)

        # Call Morph via OpenRouter
        logger.info("[MODIFY_EVENT_MORPH] Calling Morph API")
        response = await client.chat.completions.create(
            model="morph/morph-v3-large",
            messages=[{
                "role": "user",
                "content": f"<instruction>{instruction}</instruction>\n<code>{original_json}</code>\n<update>{lazy_edit}</update>"
            }]
        )

        merged_json = response.choices[0].message.content
        merged_event = json.loads(merged_json)

        logger.info("[MODIFY_EVENT_MORPH] Successfully merged event")

        # Generate field patches by diffing
        field_patches = _generate_patches_from_diff(original_event, merged_event)
        logger.info("[MODIFY_EVENT_MORPH] Generated %d field patches", len(field_patches))

        # Get target_day locator
        target_day = context.event_locators[event_id]

        # Generate patch_id
        patch_id = str(uuid.uuid4())

        # Create CalendarModifyEventPatch
        modify_patch = CalendarModifyEventPatch(
            op="modify_event",
            target_day=target_day,
            event_id=event_id,
            field_patches=field_patches,
        )

        # Add patch_id
        patch_dict = modify_patch.model_dump(mode='json')
        patch_dict['patch_id'] = patch_id

        # Add to context proposed patches
        outputs = context.agent_outputs
        proposed = outputs.setdefault('proposed_calendar_patches', [])
        proposed.append(patch_dict)

        # Queue SSE event
        immediate = outputs.setdefault('immediate_sse_events', [])
        immediate_payload = {
            'type': 'patch_proposed',
            'patch': patch_dict,
        }
        immediate.append(immediate_payload)

        logger.info("[MODIFY_EVENT_MORPH] Queued patch %s to SSE", patch_id)

        return {
            'status': 'queued',
            'patch_id': patch_id,
            'field_patch_count': len(field_patches),
        }

    except Exception as e:
        logger.error("[MODIFY_EVENT_MORPH] Failed: %s", e, exc_info=True)
        raise


def _generate_patches_from_diff(
    original: Dict[str, Any],
    merged: Dict[str, Any]
) -> List[EventFieldPatch]:
    """
    Generate EventFieldPatch operations by diffing original vs merged event.

    Converts Morph-applied changes into field patches for CalendarModifyEventPatch.
    """
    patches: List[EventFieldPatch] = []
    diff = DeepDiff(original, merged, ignore_order=False)

    # Handle value changes (modify operations)
    for path, change in diff.get('values_changed', {}).items():
        # Parse path: "root['start_time']" → field = 'start_time'
        field_match = re.search(r"\['([^']+)'\]", path)
        if field_match:
            field = field_match.group(1)

            patch = EventFieldPatch(
                op_id=uuid.uuid4().hex,
                operation="modify_field",
                field=field,
                from_value=change['old_value'],
                to_value=change['new_value'],
            )
            patches.append(patch)

    return patches
```

### Example Usage Flow

**User:** "Change the 2pm meeting to 3pm"

**Modify Event Agent → Emit Tool:**
```python
await emit_modify_event_morph(
    context_wrapper,
    event_id="abc-123",
    instruction="I'm changing the meeting start time from 2pm to 3pm",
    lazy_edit='{"start_time": "15:00", "end_time": "16:00"}'
)
```

**Morph API Call:**
```
<instruction>I'm changing the meeting start time from 2pm to 3pm</instruction>
<code>
{
  "id": "abc-123",
  "title": "Team Sync",
  "description": "Weekly standup",
  "date": "2025-11-05",
  "start_time": "14:00",
  "end_time": "15:00"
}
</code>
<update>
{"start_time": "15:00", "end_time": "16:00"}
</update>
```

**Morph Response:**
```json
{
  "id": "abc-123",
  "title": "Team Sync",
  "description": "Weekly standup",
  "date": "2025-11-05",
  "start_time": "15:00",
  "end_time": "16:00"
}
```

**Generated Patches:**
```python
[
    EventFieldPatch(
        op_id="xyz-789",
        operation="modify_field",
        field="start_time",
        from_value="14:00",
        to_value="15:00"
    ),
    EventFieldPatch(
        op_id="xyz-790",
        operation="modify_field",
        field="end_time",
        from_value="15:00",
        to_value="16:00"
    )
]
```

---

## 5. SSE Streaming & Emission Logic

### Event Flow Architecture

SSE (Server-Sent Events) enables real-time streaming of patches from backend to frontend during agent execution.

**Key Concept:** Patches are emitted **immediately** when tools execute, not buffered until end.

### Event Queue Pattern

**Location:** `context.agent_outputs['immediate_sse_events']`

Each tool execution pushes SSE events to this in-memory queue, which is polled during streaming:

```python
# In emit tool
immediate = context.agent_outputs.setdefault('immediate_sse_events', [])
immediate_payload = {
    'type': 'patch_proposed',
    'patch': patch_dict,
}
immediate.append(immediate_payload)
```

### SSE Event Types

**1. `patch_proposed`** - New patch emitted by agent tool
```json
{
  "type": "patch_proposed",
  "patch": {
    "patch_id": "abc-123",
    "op": "modify_event",
    "target_day": {...},
    "event_id": "xyz-789",
    "field_patches": [...]
  }
}
```

**2. `message_delta`** - Streaming text response from agent
```json
{
  "type": "message_delta",
  "delta": "I've updated the meeting time to 3pm..."
}
```

**3. `final`** - Complete response with all patches
```json
{
  "type": "final",
  "message": "I've updated the meeting time to 3pm. Please review the changes.",
  "patches": [...],
  "conversation_id": "conv-123"
}
```

### Chat Router Implementation

**Location:** `train-with-ai-data/app/routers/calendar/router/chat_router.py`

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from agents import RunConfig, RunContextWrapper, Runner
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar Chat"])

@router.post('/chat/{week_id}')
async def chat_with_calendar(
    week_id: str,
    request: CalendarChatRequest,
    current_user: AuthUser = Depends(get_current_user),
    db_client: SupabaseClient = Depends(get_supabase_client),
) -> StreamingResponse:
    """
    Stream calendar chat responses with real-time patch emission.

    SSE Event Types:
    - patch_proposed: New patch from agent tool
    - message_delta: Streaming text response
    - final: Complete message + all patches
    """

    # Initialize conversation manager
    conversation_manager = CalendarConversationManager(db_client)
    conversation = await conversation_manager.get_or_create_conversation(
        week_id=week_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id
    )

    # Load week context
    loader = CalendarContextLoader(db_client)
    week_data, context = await loader.load_week_context(week_id, current_user.user_id)

    # Store model_provider for sub-agents
    context.agent_outputs["model_provider"] = OPENROUTER_PROVIDER

    # Get conversation history
    history = await conversation_manager.get_conversation_context(
        conversation_id=conversation.conversation_id,
        max_turns=10
    )
    history_snippet = format_conversation_for_prompt(history)

    # Create main conversation agent
    conversation_agent = create_calendar_conversation_agent(
        week_snapshot=context.week_snapshot,
        event_locators=context.event_locators,
        conversation_history=history_snippet,
    )

    context_wrapper = RunContextWrapper(context)
    run_config = RunConfig(
        workflow_name='calendar_chat',
        model_provider=OPENROUTER_PROVIDER,
    )

    logger.info("[CALENDAR_CHAT] Starting streaming run")
    streaming_run = Runner.run_streamed(
        starting_agent=conversation_agent,
        input=request.message,
        context=context_wrapper,
        run_config=run_config,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        emitted_patch_ids: Set[str] = set()
        message_chunks: List[str] = []

        # Stream events from agent execution
        async for stream_event in streaming_run.stream_events():
            # Pull immediate events from queue (patches emitted by tools)
            immediate_events = _pull_immediate_events(context_wrapper, emitted_patch_ids)
            for payload in immediate_events:
                yield format_sse(payload)

            # Handle message deltas (streaming text)
            event_type = getattr(stream_event, 'type', '')
            if event_type == 'raw_response_event':
                delta_event = getattr(stream_event, 'data', None)
                if delta_event and getattr(delta_event, 'type', None) == 'response.output_text.delta':
                    delta_text = getattr(delta_event, 'delta', None)
                    if delta_text:
                        message_chunks.append(delta_text)
                        yield format_sse({'type': 'message_delta', 'delta': delta_text})

        # Flush remaining immediate events
        final_immediate = _pull_immediate_events(context_wrapper, emitted_patch_ids)
        for payload in final_immediate:
            yield format_sse(payload)

        # Get final message and patches
        final_output = streaming_run.final_output
        final_message = str(final_output) if isinstance(final_output, str) else ''.join(message_chunks)

        proposed_patches = context.agent_outputs.get('proposed_calendar_patches', [])
        final_patches = reconcile_patches(proposed_patches)

        # Save conversation turn
        await conversation_manager.add_conversation_turn(
            conversation_id=conversation.conversation_id,
            user_message=request.message,
            agent_response=final_message,
            patches=final_patches,
        )

        # Emit final event
        yield format_sse({
            'type': 'final',
            'message': final_message,
            'patches': _serialize_patches(final_patches),
            'conversation_id': conversation.conversation_id,
        })

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'},
    )


def _pull_immediate_events(
    context_wrapper: RunContextWrapper,
    emitted_patch_ids: Set[str],
) -> List[Dict[str, Any]]:
    """Pull and deduplicate immediate events from queue."""
    context = _resolve_context(context_wrapper)
    queue = context.agent_outputs.get('immediate_sse_events', [])
    payloads = []

    while queue:
        event = queue.pop(0)
        patch_info = event.get('patch')
        patch_id = patch_info.get('patch_id') if isinstance(patch_info, dict) else None

        # Deduplicate by patch_id
        if patch_id and patch_id in emitted_patch_ids:
            continue
        if patch_id:
            emitted_patch_ids.add(patch_id)

        payloads.append(event)

    return payloads


def format_sse(payload: Dict[str, Any]) -> str:
    """Format payload as SSE event."""
    return f"data: {json.dumps(payload)}\n\n"
```

### SSE Event Format

SSE events are formatted as:
```
data: {"type": "patch_proposed", "patch": {...}}

data: {"type": "message_delta", "delta": "I've"}

data: {"type": "message_delta", "delta": " updated"}

data: {"type": "final", "message": "...", "patches": [...]}

```

Each event is separated by `\n\n` (double newline).

---

## 6. Patch Structure for Calendar Events

### Patch Models

Calendar patches mirror the Plan Editor V2 patch structure but simplified for calendar events.

**Location:** `train-with-ai-data/app/routers/calendar/models/patches.py`

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal, List, Union

CalendarPatchOperation = Literal[
    "add_event",
    "remove_event",
    "modify_event",
    "move_event",
]

class EventInsertionAnchor(BaseModel):
    """Placement hint for inserting or moving events within a day."""
    relation: Literal["start", "end", "before", "after"]
    event_id: str | None  # Required for 'before'/'after', null for 'start'/'end'

class EventDayLocator(BaseModel):
    """Identifies a day for event placement."""
    scheduled_date: date  # YYYY-MM-DD
    anchor: EventInsertionAnchor | None

class CalendarEvent(BaseModel):
    """Simple calendar event structure."""
    title: str
    description: str = ""
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM (24-hour)
    end_time: str  # HH:MM (24-hour)
    event_id: str | None = None  # Null for new events, UUID for existing

class EventFieldPatch(BaseModel):
    """Field-level diff for event modifications."""
    op_id: str
    operation: Literal["modify_field"]
    field: str
    from_value: str | int | float | bool | None
    to_value: str | int | float | bool | None

# Patch Operations

class CalendarPatchBase(BaseModel):
    op: CalendarPatchOperation
    target_day: EventDayLocator

class CalendarAddEventPatch(CalendarPatchBase):
    op: Literal["add_event"]
    complete_event: CalendarEvent
    insertion_hint: EventInsertionAnchor

class CalendarRemoveEventPatch(CalendarPatchBase):
    op: Literal["remove_event"]
    event_id: str

class CalendarModifyEventPatch(CalendarPatchBase):
    op: Literal["modify_event"]
    event_id: str
    field_patches: List[EventFieldPatch]

class CalendarMoveEventPatch(CalendarPatchBase):
    op: Literal["move_event"]
    event_id: str
    from_day: EventDayLocator
    to_day: EventDayLocator
    post_move_adjustments: List[EventFieldPatch] | None

CalendarPatch = Union[
    CalendarAddEventPatch,
    CalendarRemoveEventPatch,
    CalendarModifyEventPatch,
    CalendarMoveEventPatch,
]
```

### Example Patches

**Add Event:**
```json
{
  "patch_id": "abc-123",
  "op": "add_event",
  "target_day": {
    "scheduled_date": "2025-11-05",
    "anchor": null
  },
  "complete_event": {
    "title": "Team Meeting",
    "description": "Weekly sync",
    "date": "2025-11-05",
    "start_time": "14:00",
    "end_time": "15:00",
    "event_id": null
  },
  "insertion_hint": {
    "relation": "end",
    "event_id": null
  }
}
```

**Modify Event:**
```json
{
  "patch_id": "def-456",
  "op": "modify_event",
  "target_day": {
    "scheduled_date": "2025-11-05",
    "anchor": null
  },
  "event_id": "xyz-789",
  "field_patches": [
    {
      "op_id": "patch-001",
      "operation": "modify_field",
      "field": "start_time",
      "from_value": "14:00",
      "to_value": "15:00"
    }
  ]
}
```

**Remove Event:**
```json
{
  "patch_id": "ghi-789",
  "op": "remove_event",
  "target_day": {
    "scheduled_date": "2025-11-05",
    "anchor": null
  },
  "event_id": "xyz-789"
}
```

**Move Event:**
```json
{
  "patch_id": "jkl-012",
  "op": "move_event",
  "target_day": {
    "scheduled_date": "2025-11-06",
    "anchor": null
  },
  "event_id": "xyz-789",
  "from_day": {
    "scheduled_date": "2025-11-05",
    "anchor": null
  },
  "to_day": {
    "scheduled_date": "2025-11-06",
    "anchor": null
  },
  "post_move_adjustments": null
}
```

---

## 7. Frontend Integration (React/Next.js)

### SSE Client Hook

**Location:** `app/hooks/useCalendarChat.ts`

```typescript
import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'

interface CalendarPatch {
  patch_id: string
  op: 'add_event' | 'remove_event' | 'modify_event' | 'move_event'
  // ... other patch fields
}

interface SSEEvent {
  type: 'patch_proposed' | 'message_delta' | 'final'
  patch?: CalendarPatch
  delta?: string
  message?: string
  patches?: CalendarPatch[]
  conversation_id?: string
}

export function useCalendarChat(weekId: string) {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamedMessage, setStreamedMessage] = useState('')
  const [proposedPatches, setProposedPatches] = useState<CalendarPatch[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)

  const sendMessage = useCallback(async (message: string) => {
    try {
      setIsStreaming(true)
      setStreamedMessage('')
      setProposedPatches([])

      // Get auth token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('No active session')

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

      // Start SSE stream
      const response = await fetch(`${API_BASE_URL}/calendar/chat/${weekId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      // Read SSE stream
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete events (separated by \n\n)
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const event of events) {
          if (!event.trim() || !event.startsWith('data: ')) continue

          try {
            const data: SSEEvent = JSON.parse(event.slice(6))

            if (data.type === 'message_delta') {
              // Append streaming text
              setStreamedMessage(prev => prev + data.delta)

            } else if (data.type === 'patch_proposed') {
              // Add patch to preview list
              setProposedPatches(prev => [...prev, data.patch!])

            } else if (data.type === 'final') {
              // Complete response
              setStreamedMessage(data.message || '')
              setProposedPatches(data.patches || [])
              if (data.conversation_id) setConversationId(data.conversation_id)
            }

          } catch (e) {
            console.error('Failed to parse SSE event:', e)
          }
        }
      }

    } catch (error) {
      console.error('Calendar chat error:', error)
    } finally {
      setIsStreaming(false)
    }
  }, [weekId, conversationId])

  return {
    sendMessage,
    isStreaming,
    streamedMessage,
    proposedPatches,
    conversationId,
  }
}
```

### Patch Preview Component

**Location:** `app/components/Calendar/PatchPreview.tsx`

```typescript
import React from 'react'
import { CalendarPatch } from './types'

interface PatchPreviewProps {
  patches: CalendarPatch[]
  onAccept: (patches: CalendarPatch[]) => void
  onReject: (patches: CalendarPatch[]) => void
}

export function PatchPreview({ patches, onAccept, onReject }: PatchPreviewProps) {
  if (patches.length === 0) return null

  return (
    <div className="patch-preview">
      <h3>Proposed Changes ({patches.length})</h3>

      <div className="patches-list">
        {patches.map((patch, idx) => (
          <div key={patch.patch_id} className="patch-item">
            <PatchDiff patch={patch} />
          </div>
        ))}
      </div>

      <div className="actions">
        <button onClick={() => onAccept(patches)} className="accept">
          ✓ Accept All
        </button>
        <button onClick={() => onReject(patches)} className="reject">
          ✗ Reject
        </button>
      </div>
    </div>
  )
}

function PatchDiff({ patch }: { patch: CalendarPatch }) {
  switch (patch.op) {
    case 'add_event':
      return (
        <div className="diff-add">
          + Add "{patch.complete_event.title}" on {patch.complete_event.date}
          at {patch.complete_event.start_time}
        </div>
      )

    case 'remove_event':
      return (
        <div className="diff-remove">
          - Remove event on {patch.target_day.scheduled_date}
        </div>
      )

    case 'modify_event':
      return (
        <div className="diff-modify">
          ✎ Modify event:
          {patch.field_patches.map(fp => (
            <div key={fp.op_id}>
              {fp.field}: <del>{fp.from_value}</del> → <ins>{fp.to_value}</ins>
            </div>
          ))}
        </div>
      )

    case 'move_event':
      return (
        <div className="diff-move">
          → Move event from {patch.from_day.scheduled_date} to {patch.to_day.scheduled_date}
        </div>
      )
  }
}
```

### Calendar Chat UI

**Location:** `app/components/Calendar/CalendarChat.tsx`

```typescript
import React, { useState } from 'react'
import { useCalendarChat } from '@/hooks/useCalendarChat'
import { PatchPreview } from './PatchPreview'

export function CalendarChat({ weekId }: { weekId: string }) {
  const [input, setInput] = useState('')
  const { sendMessage, isStreaming, streamedMessage, proposedPatches } = useCalendarChat(weekId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    await sendMessage(input.trim())
    setInput('')
  }

  const handleAccept = async (patches) => {
    // Call accept endpoint
    const response = await fetch(`/api/calendar/accept-patches/${weekId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patches }),
    })

    if (response.ok) {
      // Refresh calendar data
      window.location.reload()
    }
  }

  return (
    <div className="calendar-chat">
      <div className="chat-messages">
        {streamedMessage && (
          <div className="message ai">
            {streamedMessage}
          </div>
        )}
      </div>

      <PatchPreview
        patches={proposedPatches}
        onAccept={handleAccept}
        onReject={() => setProposedPatches([])}
      />

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Add meeting tomorrow at 2pm..."
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming || !input.trim()}>
          {isStreaming ? 'Processing...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
```

---

## 8. Accept/Reject Flow (Preview-First Architecture)

### Why Preview-First?

**Benefits:**
- **User Control**: Changes previewed before persistence
- **Error Recovery**: Easy to reject bad suggestions
- **Transparency**: Users see exactly what will change
- **Undo Support**: Can revert by rejecting patches

### Accept Endpoint

**Location:** `train-with-ai-data/app/routers/calendar/router/accept_router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from app.auth import AuthUser, get_current_user
from app.database import SupabaseClient, get_supabase_client

router = APIRouter(prefix="/calendar", tags=["Calendar Accept"])

@router.post('/accept-patches/{week_id}')
async def accept_calendar_patches(
    week_id: str,
    request: CalendarAcceptRequest,
    current_user: AuthUser = Depends(get_current_user),
    db_client: SupabaseClient = Depends(get_supabase_client),
) -> dict:
    """
    Accept and persist calendar patches to database.

    This endpoint:
    1. Validates patches against current week state
    2. Applies patches in order (add/modify/move/remove)
    3. Updates database tables
    4. Returns success/failure status
    """

    # Parse and validate patches
    patches = _parse_patches(request.patches)

    # Apply patches to database
    persistence = CalendarPersistenceService(db_client)
    result = await persistence.apply_calendar_patches(
        week_id,
        current_user.user_id,
        patches
    )

    # Record patch acceptance in conversation
    if request.conversation_id:
        conversation_manager = CalendarConversationManager(db_client)
        patch_ids = [p.patch_id for p in patches if hasattr(p, 'patch_id')]
        await conversation_manager.record_patch_action(
            conversation_id=request.conversation_id,
            accepted_ids=patch_ids
        )

    return {"status": "ok", **result}


def _parse_patches(payloads: List[dict]) -> List[CalendarPatch]:
    """Parse patch payloads into typed patch objects."""
    MODEL_BY_OP = {
        "add_event": CalendarAddEventPatch,
        "remove_event": CalendarRemoveEventPatch,
        "modify_event": CalendarModifyEventPatch,
        "move_event": CalendarMoveEventPatch,
    }

    patches = []
    for payload in payloads:
        op = payload.get("op")
        model = MODEL_BY_OP.get(op)
        if not model:
            raise HTTPException(400, f"Unsupported patch op: {op}")

        try:
            patches.append(model(**payload))
        except Exception as e:
            raise HTTPException(400, f"Invalid patch: {e}")

    return patches
```

### Persistence Service

**Location:** `train-with-ai-data/app/routers/calendar/services/persistence.py`

```python
from typing import List
import logging

logger = logging.getLogger(__name__)

class CalendarPersistenceService:
    """Applies calendar patches to database."""

    def __init__(self, db_client: SupabaseClient):
        self.db = db_client

    async def apply_calendar_patches(
        self,
        week_id: str,
        user_id: str,
        patches: List[CalendarPatch]
    ) -> dict:
        """
        Apply patches to calendar_events table.

        Patch application order:
        1. Remove events (clear space)
        2. Add events (create new)
        3. Move events (relocate)
        4. Modify events (update fields)
        """

        results = {
            'added': [],
            'removed': [],
            'modified': [],
            'moved': [],
        }

        # Group patches by operation
        remove_patches = [p for p in patches if p.op == 'remove_event']
        add_patches = [p for p in patches if p.op == 'add_event']
        move_patches = [p for p in patches if p.op == 'move_event']
        modify_patches = [p for p in patches if p.op == 'modify_event']

        # 1. Remove events
        for patch in remove_patches:
            await self._apply_remove(patch, user_id)
            results['removed'].append(patch.event_id)

        # 2. Add events
        for patch in add_patches:
            event_id = await self._apply_add(patch, user_id)
            results['added'].append(event_id)

        # 3. Move events
        for patch in move_patches:
            await self._apply_move(patch, user_id)
            results['moved'].append(patch.event_id)

        # 4. Modify events
        for patch in modify_patches:
            await self._apply_modify(patch, user_id)
            results['modified'].append(patch.event_id)

        logger.info(
            "[CALENDAR_PERSIST] Applied %d patches: %d added, %d removed, %d modified, %d moved",
            len(patches),
            len(results['added']),
            len(results['removed']),
            len(results['modified']),
            len(results['moved']),
        )

        return results

    async def _apply_add(self, patch: CalendarAddEventPatch, user_id: str) -> str:
        """Insert new event into calendar_events table."""
        event = patch.complete_event

        response = await self.db.table('calendar_events').insert({
            'user_id': user_id,
            'title': event.title,
            'description': event.description,
            'scheduled_date': event.date,
            'start_time': event.start_time,
            'end_time': event.end_time,
        }).execute()

        return response.data[0]['id']

    async def _apply_remove(self, patch: CalendarRemoveEventPatch, user_id: str):
        """Delete event from calendar_events table."""
        await self.db.table('calendar_events').delete().eq(
            'id', patch.event_id
        ).eq(
            'user_id', user_id
        ).execute()

    async def _apply_modify(self, patch: CalendarModifyEventPatch, user_id: str):
        """Update event fields in calendar_events table."""
        updates = {}

        for field_patch in patch.field_patches:
            updates[field_patch.field] = field_patch.to_value

        await self.db.table('calendar_events').update(updates).eq(
            'id', patch.event_id
        ).eq(
            'user_id', user_id
        ).execute()

    async def _apply_move(self, patch: CalendarMoveEventPatch, user_id: str):
        """Move event to different date."""
        updates = {
            'scheduled_date': patch.to_day.scheduled_date.isoformat()
        }

        # Apply post-move adjustments if any
        if patch.post_move_adjustments:
            for field_patch in patch.post_move_adjustments:
                updates[field_patch.field] = field_patch.to_value

        await self.db.table('calendar_events').update(updates).eq(
            'id', patch.event_id
        ).eq(
            'user_id', user_id
        ).execute()
```

---

## 9. Database Schema

### Calendar Events Table

```sql
-- Supabase migration: calendar_events

CREATE TABLE calendar_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  title TEXT NOT NULL,
  description TEXT DEFAULT '',

  scheduled_date DATE NOT NULL,
  start_time TIME NOT NULL,  -- HH:MM (24-hour)
  end_time TIME NOT NULL,    -- HH:MM (24-hour)

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policies
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own events"
  ON calendar_events FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own events"
  ON calendar_events FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own events"
  ON calendar_events FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own events"
  ON calendar_events FOR DELETE
  USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX idx_calendar_events_user_date
  ON calendar_events(user_id, scheduled_date);

CREATE INDEX idx_calendar_events_user_id
  ON calendar_events(user_id);
```

### Calendar Conversations Table

```sql
-- Supabase migration: calendar_conversations

CREATE TABLE calendar_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  week_id TEXT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE calendar_conversation_turns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES calendar_conversations(id) ON DELETE CASCADE,

  user_message TEXT NOT NULL,
  agent_response TEXT NOT NULL,

  patches JSONB DEFAULT '[]',
  accepted_patch_ids TEXT[] DEFAULT '{}',
  rejected_patch_ids TEXT[] DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policies
ALTER TABLE calendar_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_conversation_turns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conversations"
  ON calendar_conversations FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
  ON calendar_conversations FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own turns"
  ON calendar_conversation_turns FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM calendar_conversations
      WHERE id = conversation_id AND user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert own turns"
  ON calendar_conversation_turns FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM calendar_conversations
      WHERE id = conversation_id AND user_id = auth.uid()
    )
  );
```

---

## 10. File Structure

```
train-with-ai-data/
└── app/
    └── routers/
        └── calendar/
            ├── __init__.py
            ├── models/
            │   ├── __init__.py
            │   ├── patches.py          # Patch models (add/remove/modify/move)
            │   ├── context.py          # CalendarConversationContext
            │   ├── requests.py         # CalendarChatRequest, CalendarAcceptRequest
            │   └── responses.py        # Response models
            ├── agents/
            │   ├── __init__.py
            │   ├── conversation_agent.py  # Main routing agent
            │   ├── add_event_agent.py
            │   ├── remove_event_agent.py
            │   ├── modify_event_agent.py
            │   └── move_event_agent.py
            ├── tools/
            │   ├── __init__.py
            │   ├── emit_add_event.py
            │   ├── emit_remove_event.py
            │   ├── emit_modify_morph.py   # Morph integration
            │   └── emit_move_event.py
            ├── services/
            │   ├── __init__.py
            │   ├── context_loader.py      # Load week data
            │   ├── conversation_manager.py # Conversation persistence
            │   ├── persistence.py         # Patch application
            │   └── patch_reconciler.py    # Deduplicate patches
            └── router/
                ├── __init__.py
                ├── chat_router.py         # POST /calendar/chat/{week_id}
                ├── accept_router.py       # POST /calendar/accept-patches/{week_id}
                └── sse_events.py          # SSE formatting

trainwithai/
└── app/
    ├── hooks/
    │   └── useCalendarChat.ts         # SSE client hook
    └── components/
        └── Calendar/
            ├── CalendarChat.tsx       # Main chat UI
            ├── PatchPreview.tsx       # Patch diff preview
            └── types.ts               # TypeScript types
```

---

## 11. Implementation Checklist

### Backend (FastAPI)

- [ ] Create `calendar/` router directory structure
- [ ] Define patch models in `models/patches.py`
- [ ] Implement `CalendarConversationAgent` with 4 tools
- [ ] Create specialized agents (add/remove/modify/move)
- [ ] Implement emission tools with Morph integration
- [ ] Set up OpenRouter client and custom `ModelProvider`
- [ ] Implement SSE streaming in `chat_router.py`
- [ ] Create `accept_router.py` for patch acceptance
- [ ] Implement `CalendarPersistenceService`
- [ ] Create database migrations for `calendar_events` and conversations
- [ ] Test end-to-end flow with sample requests

### Frontend (React/Next.js)

- [ ] Create `useCalendarChat` hook for SSE streaming
- [ ] Build `CalendarChat` component
- [ ] Implement `PatchPreview` component with diff display
- [ ] Add accept/reject buttons and API calls
- [ ] Style calendar UI with patch overlays
- [ ] Test streaming and patch acceptance flow
- [ ] Add error handling and loading states

### Testing

- [ ] Unit tests for patch models
- [ ] Integration tests for agent execution
- [ ] SSE streaming tests
- [ ] Patch application tests
- [ ] Frontend component tests
- [ ] End-to-end user flow tests

---

## 12. Key Differences from Plan Editor V2

| Aspect | Plan Editor V2 | Calendar Chat |
|--------|---------------|---------------|
| **Data Model** | Training sessions (blocks, exercises) | Calendar events (title, description, time) |
| **Complexity** | High (nested structures) | Low (flat event model) |
| **Morph Usage** | Session modifications | Event modifications |
| **Patch Types** | 4 operations (add/remove/modify/move sessions) | 4 operations (add/remove/modify/move events) |
| **Time Granularity** | Days (scheduled_date) | Hours/minutes (start_time, end_time) |
| **Context Size** | Large (full training plan) | Small (single week) |

---

## 13. Next Steps

1. **Start with backend structure**: Create router directory and models
2. **Implement main conversation agent**: Set up OpenRouter and basic routing
3. **Add one operation first**: Start with `add_event` to validate end-to-end flow
4. **Test SSE streaming**: Ensure patches emit correctly
5. **Build frontend hook**: Create `useCalendarChat` for SSE consumption
6. **Implement patch preview UI**: Display changes before acceptance
7. **Add remaining operations**: Implement remove/modify/move
8. **Polish and test**: Error handling, edge cases, UX improvements

---

## 14. Common Pitfalls to Avoid

1. **Forgetting to store `model_provider` in context**: Sub-agents won't use OpenRouter
2. **Not deduplicating patches by `patch_id`**: Same patch emitted multiple times
3. **Buffering SSE events**: Emit immediately, don't wait for agent completion
4. **Ignoring conversation history**: Agent re-asks for information already provided
5. **Not using Morph for modifications**: Slower and more error-prone
6. **Applying patches in wrong order**: Remove → Add → Move → Modify
7. **Missing RLS policies**: Security vulnerability for user data

---

## 15. Performance Optimizations

1. **Parallel patch generation**: When modifying multiple events, call Morph in parallel
2. **Minimal event snapshots**: Only load current week, not entire calendar
3. **Deduplicate SSE events**: Track `emitted_patch_ids` to prevent duplicates
4. **Cache conversation history**: Store last 10 turns in memory
5. **Batch database updates**: Group patch applications in single transaction
6. **Use Morph for bulk modifications**: Apply lazy edits to multiple events simultaneously

---

## Conclusion

This architecture provides a **proven, scalable pattern** for building conversational calendar management. By following the Plan Editor V2 implementation with simplified data structures, you get:

- **Real-time user feedback** via SSE streaming
- **Preview-first safety** with accept/reject flow
- **Blazing-fast modifications** with Morph integration
- **Clean separation of concerns** via agent-as-tool pattern
- **Production-ready patterns** from existing codebase

Good luck with your hackathon! 🚀
