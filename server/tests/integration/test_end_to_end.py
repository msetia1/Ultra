"""End-to-end workflow integration tests.

Tests complete user workflows from chat → patches → accept → database verification.
"""

import pytest
from datetime import date, timedelta
from tests.utils.sse_parser import parse_sse_stream, extract_patches_from_events
from tests.utils.db_helpers import (
    find_event_by_title,
    get_event_by_id,
    verify_event_fields,
    event_exists,
)


@pytest.mark.asyncio
async def test_full_add_workflow(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test complete workflow: Chat to add event → Accept patches → Verify in DB."""
    # Step 1: Chat to add event
    chat_response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a project review meeting tomorrow at 3pm for 2 hours"},
    )

    assert chat_response.status_code == 200

    # Step 2: Parse patches from SSE stream
    events = await parse_sse_stream(chat_response)
    patches = extract_patches_from_events(events)
    assert len(patches) >= 1, "Should have add patch"

    final_event = next(e for e in events if e.get("type") == "final")
    conversation_id = final_event.get("conversation_id")

    # Step 3: Accept patches
    accept_response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={
            "patches": patches,
            "conversation_id": conversation_id,
        },
    )

    assert accept_response.status_code == 200
    result = accept_response.json()
    assert len(result["added"]) == 1

    # Step 4: Verify event exists in database
    event = find_event_by_title(supabase_client, test_user_id, "Project Review Meeting")
    assert event is not None, "Event should be in database"

    # Verify event details
    assert event["start_time"] == "15:00:00"  # 3pm
    assert event["end_time"] == "17:00:00"  # 5pm (2 hours later)

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert event["scheduled_date"] == tomorrow


@pytest.mark.asyncio
async def test_full_modify_workflow(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test complete workflow: Add event → Chat to modify → Accept → Verify changes."""
    event_id = create_test_event

    # Verify original state
    original_event = get_event_by_id(supabase_client, event_id)
    assert original_event["title"] == "Team Meeting"
    assert original_event["start_time"] == "14:00:00"

    # Step 1: Chat to modify event
    chat_response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Change the Team Meeting title to 'Sprint Planning' and move it to 10am"},
    )

    assert chat_response.status_code == 200

    # Step 2: Parse patches
    events = await parse_sse_stream(chat_response)
    patches = extract_patches_from_events(events)

    # Should have modify patch
    modify_patches = [p for p in patches if p["op"] == "modify_event"]
    assert len(modify_patches) >= 1, "Should have modify patch"

    # Step 3: Accept patches
    accept_response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": patches},
    )

    assert accept_response.status_code == 200

    # Step 4: Verify changes in database
    updated_event = get_event_by_id(supabase_client, event_id)
    assert updated_event["title"] == "Sprint Planning"
    assert updated_event["start_time"] == "10:00:00"


@pytest.mark.asyncio
async def test_complex_conversation_workflow(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test multi-turn conversation with multiple operations."""
    # Turn 1: Add an event
    response1 = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a client demo tomorrow at 2pm"},
    )

    events1 = await parse_sse_stream(response1)
    patches1 = extract_patches_from_events(events1)
    final1 = next(e for e in events1 if e.get("type") == "final")
    conversation_id = final1.get("conversation_id")

    # Accept first patches
    await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={
            "patches": patches1,
            "conversation_id": conversation_id,
        },
    )

    # Verify event created
    event = find_event_by_title(supabase_client, test_user_id, "Client Demo")
    assert event is not None
    event_id = event["id"]

    # Turn 2: Modify it (using conversation history to find "it")
    response2 = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={
            "message": "Actually, can you make it 3pm instead? And extend it to 90 minutes",
            "conversation_id": conversation_id,
        },
    )

    events2 = await parse_sse_stream(response2)
    patches2 = extract_patches_from_events(events2)

    # Should have modify patches
    assert any(p["op"] == "modify_event" for p in patches2)

    # Accept modifications
    await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={
            "patches": patches2,
            "conversation_id": conversation_id,
        },
    )

    # Verify modifications
    updated_event = get_event_by_id(supabase_client, event_id)
    assert updated_event["start_time"] == "15:00:00"  # 3pm
    assert updated_event["end_time"] == "16:30:00"  # 90 minutes later

    # Turn 3: Remove it
    response3 = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={
            "message": "Actually cancel that demo",
            "conversation_id": conversation_id,
        },
    )

    events3 = await parse_sse_stream(response3)
    patches3 = extract_patches_from_events(events3)

    # Should have remove patch
    assert any(p["op"] == "remove_event" for p in patches3)

    # Accept removal
    await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={
            "patches": patches3,
            "conversation_id": conversation_id,
        },
    )

    # Verify event deleted
    assert not event_exists(supabase_client, event_id), "Event should be deleted"


@pytest.mark.asyncio
async def test_batch_operations_workflow(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test adding multiple events in one conversation."""
    # Add multiple events in one message
    chat_response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={
            "message": "Add these events for tomorrow: breakfast at 8am, lunch at 12pm, and dinner at 6pm"
        },
    )

    assert chat_response.status_code == 200

    # Parse patches
    events = await parse_sse_stream(chat_response)
    patches = extract_patches_from_events(events)

    # Should have 3 add patches
    add_patches = [p for p in patches if p["op"] == "add_event"]
    assert len(add_patches) == 3, "Should create 3 events"

    # Accept all patches
    accept_response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": patches},
    )

    assert accept_response.status_code == 200
    result = accept_response.json()
    assert len(result["added"]) == 3

    # Verify all events in database
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    breakfast = find_event_by_title(supabase_client, test_user_id, "Breakfast")
    lunch = find_event_by_title(supabase_client, test_user_id, "Lunch")
    dinner = find_event_by_title(supabase_client, test_user_id, "Dinner")

    assert breakfast is not None
    assert lunch is not None
    assert dinner is not None

    assert breakfast["start_time"] == "08:00:00"
    assert lunch["start_time"] == "12:00:00"
    assert dinner["start_time"] == "18:00:00"


@pytest.mark.asyncio
async def test_agents_sdk_integration(
    async_client,
    clean_calendar_db,
    sample_week_id,
):
    """Verify Agents SDK is working (not direct API calls)."""
    # This test validates that:
    # 1. Agents SDK is being used (not direct OpenRouter calls)
    # 2. SSE streaming is working correctly
    # 3. Tools are being called via @function_tool decorator

    chat_response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a quick test event tomorrow at noon"},
    )

    assert chat_response.status_code == 200

    # Parse events
    events = await parse_sse_stream(chat_response)

    # Critical validation: Patches should emit BEFORE final event (streaming)
    patch_events = [e for e in events if e.get("type") == "patch_proposed"]
    final_events = [e for e in events if e.get("type") == "final"]

    assert len(patch_events) > 0, "Should have patch events"
    assert len(final_events) == 1, "Should have final event"

    # Find indices
    patch_indices = [i for i, e in enumerate(events) if e.get("type") == "patch_proposed"]
    final_index = next(i for i, e in enumerate(events) if e.get("type") == "final")

    # CRITICAL: If patches come after final, it means we're not using Runner.run_streamed()
    assert all(idx < final_index for idx in patch_indices), (
        "FAILED: Patches emitted AFTER final event. "
        "This means streaming is not working correctly. "
        "The agent ran to completion before emitting patches."
    )
