"""Integration tests for calendar accept patches endpoint.

Tests the /calendar/accept-patches/{week_id} endpoint that persists patches to database.
"""

import pytest
from datetime import date, timedelta
from tests.utils.db_helpers import (
    get_event_by_id,
    event_exists,
    find_event_by_title,
    verify_event_fields,
    get_conversation_turns,
)


@pytest.mark.asyncio
async def test_accept_add_patch(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test accepting an add event patch persists to database."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Create add patch
    add_patch = {
        "op": "add_event",
        "target_day": {
            "scheduled_date": tomorrow,
            "anchor": None,
        },
        "complete_event": {
            "title": "Test Meeting",
            "description": "Integration test",
            "date": tomorrow,
            "start_time": "10:00",
            "end_time": "11:00",
            "event_id": None,
        },
        "insertion_hint": {
            "relation": "end",
            "event_id": None,
        },
        "patch_id": "test-patch-1",
    }

    # Accept patch
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": [add_patch]},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ok"
    assert len(result["added"]) == 1

    # Verify event in database
    event = find_event_by_title(supabase_client, test_user_id, "Test Meeting")
    assert event is not None, "Event should exist in database"
    assert event["description"] == "Integration test"
    assert event["start_time"] == "10:00:00"  # Database returns with seconds
    assert event["end_time"] == "11:00:00"


@pytest.mark.asyncio
async def test_accept_remove_patch(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test accepting a remove event patch deletes from database."""
    event_id = create_test_event
    event_date = supabase_client.table("calendar_events").select("scheduled_date").eq("id", event_id).execute().data[0]["scheduled_date"]

    # Verify event exists
    assert event_exists(supabase_client, event_id), "Event should exist before removal"

    # Create remove patch
    remove_patch = {
        "op": "remove_event",
        "target_day": {
            "scheduled_date": event_date,
            "anchor": None,
        },
        "event_id": event_id,
        "patch_id": "test-patch-remove",
    }

    # Accept patch
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": [remove_patch]},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["removed"]) == 1
    assert result["removed"][0] == event_id

    # Verify event no longer exists
    assert not event_exists(supabase_client, event_id), "Event should be deleted"


@pytest.mark.asyncio
async def test_accept_modify_patch(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test accepting a modify event patch updates fields in database."""
    event_id = create_test_event
    event_date = supabase_client.table("calendar_events").select("scheduled_date").eq("id", event_id).execute().data[0]["scheduled_date"]

    # Create modify patch with field changes
    modify_patch = {
        "op": "modify_event",
        "target_day": {
            "scheduled_date": event_date,
            "anchor": None,
        },
        "event_id": event_id,
        "field_patches": [
            {
                "op_id": "field-1",
                "operation": "modify_field",
                "field": "title",
                "from_value": "Team Meeting",
                "to_value": "Leadership Sync",
            },
            {
                "op_id": "field-2",
                "operation": "modify_field",
                "field": "start_time",
                "from_value": "14:00",
                "to_value": "15:00",
            },
        ],
        "patch_id": "test-patch-modify",
    }

    # Accept patch
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": [modify_patch]},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["modified"]) == 1

    # Verify changes in database
    event = get_event_by_id(supabase_client, event_id)
    assert event["title"] == "Leadership Sync"
    assert event["start_time"] == "15:00:00"


@pytest.mark.asyncio
async def test_accept_move_patch(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test accepting a move event patch changes the date."""
    event_id = create_test_event
    original_event = get_event_by_id(supabase_client, event_id)
    original_date = original_event["scheduled_date"]

    # New date (2 days later)
    new_date = (date.fromisoformat(original_date) + timedelta(days=2)).isoformat()

    # Create move patch
    move_patch = {
        "op": "move_event",
        "target_day": {
            "scheduled_date": new_date,
            "anchor": None,
        },
        "event_id": event_id,
        "from_day": {
            "scheduled_date": original_date,
            "anchor": None,
        },
        "to_day": {
            "scheduled_date": new_date,
            "anchor": None,
        },
        "post_move_adjustments": None,
        "patch_id": "test-patch-move",
    }

    # Accept patch
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": [move_patch]},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["moved"]) == 1

    # Verify date change in database
    event = get_event_by_id(supabase_client, event_id)
    assert event["scheduled_date"] == new_date


@pytest.mark.asyncio
async def test_accept_multiple_patches(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test accepting multiple patches in one request."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Create 3 add patches
    patches = []
    for i in range(3):
        patches.append({
            "op": "add_event",
            "target_day": {
                "scheduled_date": tomorrow,
                "anchor": None,
            },
            "complete_event": {
                "title": f"Event {i+1}",
                "description": f"Test event {i+1}",
                "date": tomorrow,
                "start_time": f"{9+i}:00",
                "end_time": f"{10+i}:00",
                "event_id": None,
            },
            "insertion_hint": {
                "relation": "end",
                "event_id": None,
            },
            "patch_id": f"test-patch-{i+1}",
        })

    # Accept all patches
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={"patches": patches},
    )

    assert response.status_code == 200
    result = response.json()
    assert len(result["added"]) == 3

    # Verify all events in database
    for i in range(3):
        event = find_event_by_title(supabase_client, test_user_id, f"Event {i+1}")
        assert event is not None


@pytest.mark.asyncio
async def test_conversation_turn_tracking(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that patch acceptance is tracked in conversation turns."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # First create a conversation by chatting
    from tests.utils.sse_parser import parse_sse_stream

    chat_response = await async_client.post(
        f"/calendar/chat/{sample_week_id}",
        json={"message": "Add a morning standup at 9am tomorrow"},
    )
    events = await parse_sse_stream(chat_response)
    final_event = next(e for e in events if e.get("type") == "final")
    conversation_id = final_event.get("conversation_id")
    patches = final_event.get("patches", [])

    # Accept patches with conversation_id
    response = await async_client.post(
        f"/calendar/accept-patches/{sample_week_id}",
        json={
            "patches": patches,
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200

    # Verify conversation turn has accepted_patch_ids
    turns = get_conversation_turns(supabase_client, conversation_id)
    assert len(turns) > 0

    # Most recent turn should have accepted_patch_ids
    last_turn = turns[-1]
    assert "accepted_patch_ids" in last_turn
    assert len(last_turn["accepted_patch_ids"]) > 0
