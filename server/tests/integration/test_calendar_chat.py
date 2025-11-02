"""Integration tests for calendar chat endpoint.

Tests the /calendar/chat/{week_id} SSE streaming endpoint with real agent execution.
"""

import pytest
from tests.utils.sse_parser import (
    parse_sse_stream,
    extract_patches_from_events,
    extract_final_message,
    verify_real_time_emission,
)
from tests.utils.db_helpers import (
    get_events_for_week,
    find_event_by_title,
)


@pytest.mark.asyncio
async def test_add_event_via_chat(async_client, clean_calendar_db, sample_week_id, supabase_client, test_user_id):
    """Test adding a calendar event via chat message."""
    # Send chat message to add event
    response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a team standup tomorrow at 9am for 30 minutes"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE stream
    events = await parse_sse_stream(response)
    assert len(events) > 0, "Should receive SSE events"

    # Verify we got patches
    patches = extract_patches_from_events(events)
    assert len(patches) >= 1, "Should have at least one add patch"

    # Verify patch structure
    add_patch = patches[0]
    assert add_patch["op"] == "add_event"
    assert "complete_event" in add_patch
    assert "patch_id" in add_patch

    # Verify event details
    event = add_patch["complete_event"]
    assert "standup" in event["title"].lower() or "team" in event["title"].lower()
    assert event["start_time"] == "09:00"

    # Verify final message exists
    final_msg = extract_final_message(events)
    assert final_msg, "Should have final agent message"

    # Verify real-time streaming (patches came before final)
    assert verify_real_time_emission(events), "Patches should emit in real-time"


@pytest.mark.asyncio
async def test_remove_event_via_chat(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test removing a calendar event via chat message."""
    # Get the event ID from fixture
    event_id = create_test_event

    # Send chat message to remove event
    response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Remove the Team Meeting event"},
    )

    assert response.status_code == 200

    # Parse SSE stream
    events = await parse_sse_stream(response)
    patches = extract_patches_from_events(events)

    # Should have remove patch
    assert any(p["op"] == "remove_event" for p in patches), "Should have remove patch"

    remove_patch = next(p for p in patches if p["op"] == "remove_event")
    assert "event_id" in remove_patch
    assert "patch_id" in remove_patch


@pytest.mark.asyncio
async def test_modify_event_via_chat(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test modifying event fields using Morph API."""
    event_id = create_test_event

    # Send chat message to modify event
    response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Change the Team Meeting to 3pm instead of 2pm"},
    )

    assert response.status_code == 200

    # Parse SSE stream
    events = await parse_sse_stream(response)
    patches = extract_patches_from_events(events)

    # Should have modify patch with field changes
    modify_patches = [p for p in patches if p["op"] == "modify_event"]
    assert len(modify_patches) >= 1, "Should have modify patch"

    modify_patch = modify_patches[0]
    assert "field_patches" in modify_patch
    assert len(modify_patch["field_patches"]) > 0

    # Verify time change in field patches
    field_patches = modify_patch["field_patches"]
    time_changes = [
        fp for fp in field_patches if fp["field"] in ["start_time", "end_time"]
    ]
    assert len(time_changes) > 0, "Should have time field changes"


@pytest.mark.asyncio
async def test_move_event_via_chat(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test moving an event to a different date."""
    event_id = create_test_event

    # Send chat message to move event
    response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Move the Team Meeting to next Monday"},
    )

    assert response.status_code == 200

    # Parse SSE stream
    events = await parse_sse_stream(response)
    patches = extract_patches_from_events(events)

    # Should have move patch
    move_patches = [p for p in patches if p["op"] == "move_event"]
    assert len(move_patches) >= 1, "Should have move patch"

    move_patch = move_patches[0]
    assert "from_day" in move_patch
    assert "to_day" in move_patch
    assert move_patch["from_day"]["scheduled_date"] != move_patch["to_day"]["scheduled_date"]


@pytest.mark.asyncio
async def test_conversation_history(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test multi-turn conversation maintains context."""
    # First message: Add event
    response1 = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a meeting tomorrow at 2pm"},
    )
    events1 = await parse_sse_stream(response1)

    # Extract conversation_id from final event
    final_event = next(e for e in events1 if e.get("type") == "final")
    conversation_id = final_event.get("conversation_id")
    assert conversation_id, "Should have conversation_id in final event"

    # Second message: Modify the event (should use history to find "the meeting")
    response2 = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={
            "message": "Actually, make it 3pm instead",
            "conversation_id": conversation_id,
        },
    )
    events2 = await parse_sse_stream(response2)
    patches2 = extract_patches_from_events(events2)

    # Should understand "it" refers to the meeting from previous turn
    assert any(p["op"] == "modify_event" for p in patches2), "Should modify the previously added event"


@pytest.mark.asyncio
async def test_sse_streaming_real_time(
    async_client,
    clean_calendar_db,
    sample_week_id,
):
    """Verify patches emit DURING agent execution, not after."""
    response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add breakfast at 8am, lunch at 12pm, and dinner at 6pm"},
    )

    events = await parse_sse_stream(response)

    # Should have multiple patch_proposed events that come BEFORE final event
    patch_events = [e for e in events if e.get("type") == "patch_proposed"]
    final_events = [e for e in events if e.get("type") == "final"]

    assert len(patch_events) >= 3, "Should emit 3 patches for 3 events"
    assert len(final_events) == 1, "Should have exactly one final event"

    # Critical: Verify patches came before final (real-time streaming)
    assert verify_real_time_emission(events), "Patches MUST emit in real-time, not after completion"
