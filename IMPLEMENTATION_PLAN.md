# Calendar Chat Implementation Plan

## Executive Summary

Building a conversational calendar management system where users can modify their weekly calendar through natural language. The system uses SSE streaming for real-time feedback, a preview-first architecture for user control, and OpenRouter API for LLM capabilities.

## Current State

**Backend (`/server`)**:
- Monolithic FastAPI app (406 lines in `app.py`)
- Supabase integration exists
- No OpenAI SDK or agents framework installed
- Development uses `TEST_USER_ID` pattern

**Frontend (`/frontend`)**:
- Vite + React + TypeScript stack
- Calendar feature with Zustand store (uses "Task" model)
- ChatPanel UI skeleton exists but not functional
- No SSE client or patch preview UI

**Database**:
- No calendar events table
- No conversation history tables
- Migration infrastructure exists

## Architecture Overview

### Agent Pattern
Single conversation agent routes user intent to 4 specialized sub-agents:
- **Add Event Agent**: Creates new calendar events
- **Remove Event Agent**: Deletes events
- **Modify Event Agent**: Updates event fields using Morph API
- **Move Event Agent**: Relocates events to different dates/times

### Data Flow
1. User sends message via ChatPanel
2. Frontend opens SSE stream to backend
3. Backend conversation agent classifies intent
4. Specialized agent executes and emits patches
5. Patches streamed to frontend in real-time
6. User previews changes and accepts/rejects
7. Accepted patches persisted to database

### Key Technologies
- **OpenRouter**: Unified LLM API (using `anthropic/claude-3.5-sonnet`)
- **Morph API**: Fast lazy edits for event modifications (`morph/morph-v3-large`)
- **SSE**: Server-Sent Events for real-time streaming
- **DeepDiff**: Generate field-level patches from object diffs

## Implementation Phases

### Phase 1: Foundation (Database & Dependencies)

**Dependencies**:
- Add `openai` SDK (connects to OpenRouter)
- Add `deepdiff` for patch generation
- Add `sse-starlette` for streaming responses

**Database Migrations**:
- `calendar_events`: Store user events (id, user_id, title, description, scheduled_date, start_time, end_time)
- `calendar_conversations`: Track chat sessions (id, user_id, week_id)
- `calendar_conversation_turns`: Store conversation history (id, conversation_id, user_message, agent_response, patches)

**Environment**:
- Add `OPENROUTER_API_KEY` to server environment

### Phase 2: Backend Structure

Refactor from monolithic app to modular router pattern:

**Router Structure**:
- `routers/calendar/models/`: Pydantic models for patches, requests, responses
- `routers/calendar/agents/`: Agent creation and orchestration logic
- `routers/calendar/tools/`: Patch emission functions
- `routers/calendar/services/`: Business logic (context loading, persistence, patch reconciliation)
- `routers/calendar/routers/`: HTTP endpoints (chat, accept-patches)

### Phase 3: Agent Implementation

**Manual Agent Pattern** (no SDK dependency):
Use OpenAI SDK's function calling feature to implement agent behavior:
- Conversation agent uses function calling to invoke sub-agents
- Each sub-agent is a focused function with specific tools
- Tools emit patches to shared context
- Manual orchestration instead of framework-based

**Conversation Agent**:
- Receives user message
- Analyzes intent (add/remove/modify/move)
- Calls appropriate specialized agent function
- Returns conversational response

**Specialized Agents**:
- Each has narrow responsibility
- Receives extracted intent from conversation agent
- Has access to emission tools
- Returns status and patch count

### Phase 4: Patch System

**Patch Types** (4 operations):
- `CalendarAddEventPatch`: Complete event data + insertion hint
- `CalendarRemoveEventPatch`: Event ID to delete
- `CalendarModifyEventPatch`: Event ID + field-level diffs
- `CalendarMoveEventPatch`: Event ID + from/to dates + optional adjustments

**Patch Models**:
- EventDayLocator: Identifies target date and position
- EventInsertionAnchor: Placement hints (start/end/before/after)
- EventFieldPatch: Individual field change with from/to values

**Emission Flow**:
1. Tool generates patch object
2. Assigns unique patch_id
3. Adds to context proposed patches list
4. Queues SSE event for immediate streaming
5. Returns status to agent

### Phase 5: SSE Streaming

**Event Types**:
- `patch_proposed`: New patch emitted by tool
- `message_delta`: Streaming agent response text
- `final`: Complete response with all patches

**Implementation**:
- Use `sse-starlette.EventSourceResponse`
- Poll immediate events queue during stream
- Deduplicate by patch_id
- Flush remaining events at end

**Router Endpoint**:
- `POST /calendar/chat/{week_id}` returns SSE stream
- Accepts user message + optional conversation_id
- Loads week context and conversation history
- Streams patches and messages in real-time

### Phase 6: Morph Integration

**Purpose**: Fast, precise event modifications without hallucinations

**Implementation**:
- Use OpenRouter to call `morph/morph-v3-large`
- Send instruction + original event JSON + lazy edit
- Receive merged event back
- Generate field patches via DeepDiff
- Emit modify patch with field-level changes

**Benefits**:
- 10,500+ tokens/sec (3x faster than standard generation)
- No hallucinations (only applies specified changes)
- Automatic diff generation

### Phase 7: Persistence Service

**Accept Endpoint**:
- `POST /calendar/accept-patches/{week_id}`
- Validates patches against current state
- Applies in order: remove → add → move → modify
- Updates database tables
- Records action in conversation history

**Database Operations**:
- Add: Insert new row in calendar_events
- Remove: Delete by event_id
- Modify: Update specific fields
- Move: Update scheduled_date + optional time adjustments

### Phase 8: Frontend Integration

**TypeScript Types**:
- Define patch interfaces matching backend Pydantic models
- Add SSE event types
- Create calendar event model (align with backend)

**SSE Client Hook** (`useCalendarChat`):
- Manages SSE connection lifecycle
- Parses streaming events
- Accumulates message deltas
- Collects proposed patches
- Provides send message function

**Patch Preview Component**:
- Displays list of proposed patches
- Shows visual diff for each patch type
- Accept/reject buttons
- Calls accept endpoint on confirmation

**ChatPanel Updates**:
- Input field for user messages
- Streaming message display
- Patch preview integration
- Loading and error states

### Phase 9: Data Model Alignment

**Terminology Consolidation**:
- Frontend uses "Task" → migrate to "CalendarEvent"
- Backend uses "Event" → consistent naming
- Update all types, interfaces, and variables

**Format Standardization**:
- Dates: ISO 8601 strings (YYYY-MM-DD)
- Times: 24-hour format (HH:MM)
- Timestamps: ISO 8601 with timezone

**Store Updates**:
- Add week_id generation (YYYY-WXX format)
- Load events from Supabase instead of mock data
- Handle optimistic updates from patches
- Sync after patch acceptance

### Phase 10: Context Loading Service

**Week Context Loader**:
- Fetches all events for target week
- Builds event_locators map (event_id → date + anchor)
- Creates week snapshot for agent context
- Loads conversation history (last 10 turns)

**Context Object**:
- week_snapshot: Complete week data with events
- event_locators: Quick event positioning lookup
- agent_outputs: Shared state for patches and SSE events
- conversation_history: Recent user/agent exchanges

### Phase 11: Conversation Management

**Manager Service**:
- Get or create conversation for week
- Add conversation turns after completion
- Record patch acceptance/rejection
- Format history for agent prompts

**History Formatting**:
- Last 10 turns condensed into readable format
- Includes user messages and agent responses
- Notes which patches were accepted
- Prevents re-asking for known information

## Testing Strategy

**Unit Tests**:
- Patch model validation
- Diff generation accuracy
- Agent intent classification

**Integration Tests**:
- SSE streaming flow
- Patch application order
- Database persistence

**End-to-End Tests**:
- Full conversation flow
- Accept/reject workflows
- Error handling paths

## Risk Mitigations

**No Agents SDK**: Implement agent pattern manually using OpenAI function calling
**SSE Failures**: Fallback to polling or error state in UI
**Morph Unavailable**: Fall back to standard LLM generation for modifications
**Patch Conflicts**: Validate current state before applying, reject stale patches

## Success Criteria

- [ ] User can add events via natural language
- [ ] User can remove events via natural language
- [ ] User can modify event details via natural language
- [ ] User can move events to different dates/times
- [ ] Patches preview before persistence
- [ ] Changes stream in real-time during agent thinking
- [ ] Conversation history prevents redundant questions
- [ ] All changes persist correctly to database

## Timeline Estimate

- Phase 1-2 (Foundation + Structure): 2-3 hours
- Phase 3-4 (Agents + Patches): 3-4 hours
- Phase 5-7 (SSE + Morph + Persistence): 3-4 hours
- Phase 8-9 (Frontend + Alignment): 2-3 hours
- Phase 10-11 (Context + Conversation): 1-2 hours
- Testing & Polish: 2-3 hours

**Total**: 13-19 hours
