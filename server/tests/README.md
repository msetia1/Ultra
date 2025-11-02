# Calendar Chat Integration Tests

Integration tests for the calendar chat system that validate the Agents SDK migration.

## Overview

These tests **hit actual running endpoints** (not mocks) to verify:
- ✅ OpenAI Agents SDK integration with OpenRouter
- ✅ Real-time SSE streaming (patches emit DURING execution)
- ✅ All 4 calendar operations (add/remove/modify/move)
- ✅ Database persistence via Supabase
- ✅ Conversation history tracking
- ✅ Morph API integration for modifications

## Setup

### 1. Install Test Dependencies

```bash
cd server
pip install -r requirements.txt
```

This installs:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client (already in requirements)

### 2. Configure Environment

Ensure your `.env` file has:
```bash
# OpenRouter (required for Agents SDK)
OPENROUTER_API_KEY=your_key_here

# Supabase (required for database)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Test user (optional, defaults to all-zeros UUID)
TEST_USER_ID=00000000-0000-0000-0000-000000000000
```

### 3. Run Database Migrations

```bash
cd server/supabase
supabase migration up
```

## Running Tests

**IMPORTANT**: These integration tests hit actual running endpoints. You must start the FastAPI server before running tests.

### Step 1: Start the FastAPI Server

```bash
# From server/ directory
uvicorn app:app --reload --port 8000
```

Keep this server running in a separate terminal window.

### Step 2: Run All Integration Tests

```bash
# In a new terminal window, from server/ directory
pytest tests/integration/ -v
```

**Optional**: Configure custom server URL:
```bash
# If server is running on a different port/host
TEST_API_BASE_URL=http://localhost:8001 pytest tests/integration/ -v
```

### Run Specific Test File

```bash
# Chat endpoint tests
pytest tests/integration/test_calendar_chat.py -v

# Accept endpoint tests
pytest tests/integration/test_calendar_accept.py -v

# End-to-end workflows
pytest tests/integration/test_end_to_end.py -v
```

### Run Specific Test

```bash
pytest tests/integration/test_calendar_chat.py::test_add_event_via_chat -v
```

### Run with Output (See SSE Events)

```bash
pytest tests/integration/ -v -s
```

### Run with Coverage

```bash
pytest tests/integration/ --cov=routers.calendar --cov-report=html
```

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── utils/
│   ├── sse_parser.py             # Parse SSE streams from responses
│   └── db_helpers.py             # Database verification utilities
└── integration/
    ├── test_calendar_chat.py     # Chat endpoint tests (SSE streaming)
    ├── test_calendar_accept.py   # Accept endpoint tests (persistence)
    └── test_end_to_end.py        # Full workflow tests (chat → accept → verify)
```

## Test Coverage

### Chat Endpoint Tests (`test_calendar_chat.py`)

- ✅ `test_add_event_via_chat` - Add event via natural language
- ✅ `test_remove_event_via_chat` - Remove existing event
- ✅ `test_modify_event_via_chat` - Modify event fields using Morph
- ✅ `test_move_event_via_chat` - Move event to different date
- ✅ `test_conversation_history` - Multi-turn conversation with context
- ✅ `test_sse_streaming_real_time` - **CRITICAL**: Verify patches emit in real-time

### Accept Endpoint Tests (`test_calendar_accept.py`)

- ✅ `test_accept_add_patch` - Persist add patch to database
- ✅ `test_accept_remove_patch` - Delete event from database
- ✅ `test_accept_modify_patch` - Update event fields
- ✅ `test_accept_move_patch` - Change event date
- ✅ `test_accept_multiple_patches` - Batch operations
- ✅ `test_conversation_turn_tracking` - Track accepted patches

### End-to-End Workflow Tests (`test_end_to_end.py`)

- ✅ `test_full_add_workflow` - Chat → Accept → Verify in DB
- ✅ `test_full_modify_workflow` - Add → Modify → Accept → Verify
- ✅ `test_complex_conversation_workflow` - Multi-turn with add/modify/remove
- ✅ `test_batch_operations_workflow` - Multiple events in one message
- ✅ `test_agents_sdk_integration` - **CRITICAL**: Validate streaming works

## Key Validations

### Real-Time Streaming ⚡

The most important validation is in `test_sse_streaming_real_time()`:

```python
# CRITICAL: Patches MUST emit BEFORE final event
assert verify_real_time_emission(events), "Patches should emit in real-time"
```

This verifies that:
1. We're using `Runner.run_streamed()` (not `Runner.run()`)
2. Tools emit patches **AS THEY HAPPEN** (not after completion)
3. The Agents SDK migration is working correctly

### Database Verification ✅

All tests verify actual database state:
- Events exist after add patches
- Events deleted after remove patches
- Fields updated after modify patches
- Dates changed after move patches

### Conversation Tracking 💬

Tests verify conversation history:
- Conversation IDs generated and tracked
- Turns saved with messages and patches
- Accepted patches recorded on turns
- Context maintained across turns

## Troubleshooting

### "Patches emitted AFTER final event"

This means SSE streaming is **not working correctly**. The agent is running to completion before emitting patches. Check:
1. `chat_router.py` is using `Runner.run_streamed()` (not `Runner.run()`)
2. `_pull_immediate_events()` is called inside the stream loop
3. Tools are decorated with `@function_tool`

### "OPENROUTER_API_KEY not found"

Set your OpenRouter API key in `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

### "Supabase RLS policy violation"

The test user (all-zeros UUID) might not have proper permissions. Either:
1. Disable RLS for testing
2. Create a real test user with proper auth
3. Use the service role key (bypasses RLS)

### "No events found in database"

Check:
1. Migrations are applied (`supabase migration up`)
2. Database connection is working
3. Test cleanup isn't too aggressive (use `clean_calendar_db` fixture)

## Success Criteria ✅

Tests pass when:
- All 4 calendar operations work end-to-end
- SSE streaming emits patches in real-time (before final event)
- Agents SDK successfully routes through OpenRouter
- Database persistence works correctly
- Conversation history tracks turns and patches
- Multi-turn conversations maintain context

## Example Output

```bash
$ pytest tests/integration/test_calendar_chat.py -v

tests/integration/test_calendar_chat.py::test_add_event_via_chat PASSED     [ 16%]
tests/integration/test_calendar_chat.py::test_remove_event_via_chat PASSED  [ 33%]
tests/integration/test_calendar_chat.py::test_modify_event_via_chat PASSED  [ 50%]
tests/integration/test_calendar_chat.py::test_move_event_via_chat PASSED    [ 66%]
tests/integration/test_calendar_chat.py::test_conversation_history PASSED   [ 83%]
tests/integration/test_calendar_chat.py::test_sse_streaming_real_time PASSED [100%]

========================== 6 passed in 45.23s ===========================
```

## Notes

- Tests use the **actual FastAPI app** (not mocks)
- Tests hit **real Supabase database** (use test user)
- Tests make **real API calls** to OpenRouter (costs money!)
- Tests are **async** (use `pytest-asyncio`)
- Database is cleaned before/after each test
- Each test is independent (no shared state)
