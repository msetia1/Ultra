"""Integration tests for calendar week generation endpoint.

Tests the /calendar/generate-week/{week_id} SSE streaming endpoint that uses
LLM to generate balanced weekly schedules.
"""

import pytest
from datetime import date, timedelta
from tests.utils.sse_parser import parse_sse_stream
from tests.utils.db_helpers import (
    get_events_for_week,
    find_event_by_title,
    get_event_by_id,
)


@pytest.mark.asyncio
async def test_generate_week_basic(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test basic week generation with streaming response."""
    # Generate week events
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={
            "user_goals": "productivity and wellness",
        },
        timeout=None,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE stream
        events = await parse_sse_stream(response)
        assert len(events) > 0, "Should receive SSE events"

    # Verify event types in stream
    event_types = [e.get("event_type") for e in events]
    assert "streaming_started" in event_types, "Should have streaming_started event"
    assert "generation_complete" in event_types, "Should have generation_complete event"

    # Verify we got event_ready events
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]
    assert len(event_ready_events) >= 10, "Should generate at least 10 events for the week"
    assert len(event_ready_events) <= 30, "Should not generate more than 30 events"

    # Verify generation_complete has total count
    complete_event = next(e for e in events if e.get("event_type") == "generation_complete")
    assert complete_event.get("total_events") > 0
    assert complete_event.get("progress") == 100


@pytest.mark.asyncio
async def test_generated_events_stored_in_db(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that generated events are stored in database."""
    # Generate week events
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "focus on deep work"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Extract event_ready events
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]
    assert len(event_ready_events) > 0, "Should have generated events"

    # Verify events are in database
    db_events = get_events_for_week(supabase_client, test_user_id, sample_week_id)
    assert len(db_events) == len(event_ready_events), "All generated events should be in DB"

    # Verify event data integrity
    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        event_id = sse_event.get("event_id")

        # Find in database
        if event_id:
            db_event = get_event_by_id(supabase_client, event_id)
            assert db_event is not None, f"Event {event_id} should exist in DB"

            # Verify key fields match
            assert db_event["title"] == event_data["title"]
            assert db_event["description"] == event_data["description"]
            assert db_event["scheduled_date"] == event_data["scheduled_date"]
            assert db_event["start_time"][:5] == event_data["start_time"]  # Compare HH:MM (DB has seconds)
            assert db_event["end_time"][:5] == event_data["end_time"]


@pytest.mark.asyncio
async def test_generated_events_within_week_boundaries(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that all generated events fall within the specified week."""
    # Parse week boundaries
    year, week_num = sample_week_id.split("-W")
    year, week_num = int(year), int(week_num)

    # Calculate week start and end dates (ISO week)
    from datetime import datetime
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4.date() - timedelta(days=jan_4.weekday())
    week_start = week_1_start + timedelta(weeks=week_num - 1)
    week_end = week_start + timedelta(days=6)

    # Generate week events
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "balanced schedule"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Check all event dates are within boundaries
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]

    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        event_date = date.fromisoformat(event_data["scheduled_date"])

        assert week_start <= event_date <= week_end, (
            f"Event '{event_data['title']}' on {event_date} is outside week "
            f"boundaries [{week_start}, {week_end}]"
        )


@pytest.mark.asyncio
async def test_real_time_streaming_emission(
    async_client,
    clean_calendar_db,
    sample_week_id,
):
    """Verify events emit DURING generation, not after (real-time streaming)."""
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "productivity"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Should have multiple event_ready events that come BEFORE generation_complete
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]
    complete_events = [e for e in events if e.get("event_type") == "generation_complete"]

    assert len(event_ready_events) >= 10, "Should emit multiple events"
    assert len(complete_events) == 1, "Should have exactly one completion event"

    # Critical: Verify events came before completion (real-time streaming)
    event_indices = []
    complete_index = None

    for i, event in enumerate(events):
        if event.get("event_type") == "event_ready":
            event_indices.append(i)
        elif event.get("event_type") == "generation_complete":
            complete_index = i

    # All event_ready events should come before generation_complete
    assert all(idx < complete_index for idx in event_indices), (
        "Events MUST emit in real-time during generation, not batched at the end"
    )


@pytest.mark.asyncio
async def test_generation_with_user_goals(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that user goals influence generated events."""
    # Generate with fitness focus
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={
            "user_goals": "focus on fitness and exercise",
        },
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Extract generated events
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]

    # Should have fitness-related events
    fitness_keywords = ["workout", "exercise", "gym", "run", "fitness", "training"]
    fitness_events = []

    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        title_lower = event_data["title"].lower()
        desc_lower = event_data["description"].lower()

        if any(keyword in title_lower or keyword in desc_lower for keyword in fitness_keywords):
            fitness_events.append(event_data)

    assert len(fitness_events) >= 3, (
        f"With 'fitness and exercise' goals, should generate at least 3 fitness events. "
        f"Found {len(fitness_events)}"
    )


@pytest.mark.asyncio
async def test_generation_with_user_context(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that user context constrains event scheduling."""
    # Generate with specific work hours constraint
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={
            "user_goals": "productivity",
            "user_context": {
                "work_hours": "9am-5pm",
                "timezone": "UTC",
            },
        },
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Extract events
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]

    # Verify events have valid times (not too early or too late)
    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        start_time = event_data["start_time"]

        # Parse hour from HH:MM format
        hour = int(start_time.split(":")[0])

        # Events should generally be in reasonable hours (not too extreme)
        assert 6 <= hour <= 23, (
            f"Event '{event_data['title']}' at {start_time} is outside reasonable hours"
        )


@pytest.mark.asyncio
async def test_generation_with_existing_events(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
    create_test_event,
):
    """Test generation considers existing events to avoid conflicts."""
    # Pre-create an event using fixture
    existing_event_id = create_test_event
    existing_event = get_event_by_id(supabase_client, existing_event_id)

    # Generate week events
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={
            "user_goals": "productivity",
            # existing_events will be fetched automatically by the endpoint
        },
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Verify generation completed successfully
    complete_events = [e for e in events if e.get("event_type") == "generation_complete"]
    assert len(complete_events) == 1

    # Verify existing event still exists
    assert get_event_by_id(supabase_client, existing_event_id) is not None

    # Verify new events were generated
    all_events = get_events_for_week(supabase_client, test_user_id, sample_week_id)
    assert len(all_events) > 1, "Should have existing event plus new generated events"


@pytest.mark.asyncio
async def test_event_data_structure(
    async_client,
    clean_calendar_db,
    sample_week_id,
):
    """Test that generated events have correct data structure."""
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "balanced week"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]

    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]

        # Required fields
        assert "title" in event_data, "Event must have title"
        assert "description" in event_data, "Event must have description"
        assert "scheduled_date" in event_data, "Event must have scheduled_date"
        assert "start_time" in event_data, "Event must have start_time"
        assert "end_time" in event_data, "Event must have end_time"

        # Validate formats
        # Date format: YYYY-MM-DD
        date.fromisoformat(event_data["scheduled_date"])

        # Time format: HH:MM
        start_parts = event_data["start_time"].split(":")
        assert len(start_parts) == 2, "start_time should be HH:MM format"
        assert 0 <= int(start_parts[0]) <= 23, "Invalid hour in start_time"
        assert 0 <= int(start_parts[1]) <= 59, "Invalid minute in start_time"

        end_parts = event_data["end_time"].split(":")
        assert len(end_parts) == 2, "end_time should be HH:MM format"

        # Optional fields (if present, validate them)
        if "event_type" in event_data:
            assert isinstance(event_data["event_type"], str)

        if "priority" in event_data:
            assert event_data["priority"] in ["high", "medium", "low"]


@pytest.mark.asyncio
async def test_generation_error_handling_invalid_week(
    async_client,
    clean_calendar_db,
):
    """Test error handling for invalid week ID format."""
    # Use invalid week ID
    invalid_week_id = "2025-INVALID"

    response = await async_client.post(
        f"/calendar/generate-week/{invalid_week_id}",
        json={"user_goals": "productivity"},
    )

    # Should return error (400 or 500)
    assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_event_variety_and_balance(
    async_client,
    clean_calendar_db,
    sample_week_id,
    supabase_client,
    test_user_id,
):
    """Test that generated events show variety and balance across the week."""
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "balanced lifestyle"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]

    # Count events per day
    events_by_date = {}
    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        event_date = event_data["scheduled_date"]

        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event_data)

    # Should have events on multiple days (not all on one day)
    assert len(events_by_date) >= 3, "Events should be distributed across multiple days"

    # Should not have too many events on a single day
    for event_date, day_events in events_by_date.items():
        assert len(day_events) <= 8, (
            f"Date {event_date} has {len(day_events)} events - should not overload single day"
        )

    # Check for variety in event types if present
    event_types = set()
    for sse_event in event_ready_events:
        event_data = sse_event["event_data"]
        if "event_type" in event_data:
            event_types.add(event_data["event_type"])

    # If event_type is used, should have some variety
    if event_types:
        assert len(event_types) >= 2, "Should have variety in event types"


@pytest.mark.asyncio
async def test_event_progress_tracking(
    async_client,
    clean_calendar_db,
    sample_week_id,
):
    """Test that progress is tracked correctly during generation."""
    async with async_client.stream(
        "POST",
        f"/calendar/generate-week/{sample_week_id}",
        json={"user_goals": "productivity"},
        timeout=None,
    ) as response:
        events = await parse_sse_stream(response)

    # Verify progress increases over time
    progress_values = []
    for event in events:
        if "progress" in event:
            progress_values.append(event["progress"])

    # Progress should generally increase (allowing for some variation)
    assert progress_values[0] < progress_values[-1], "Progress should increase"
    assert progress_values[-1] == 100, "Final progress should be 100"

    # Verify event_number increments for event_ready events
    event_ready_events = [e for e in events if e.get("event_type") == "event_ready"]
    event_numbers = [e.get("event_number") for e in event_ready_events]

    # Should be sequential: 1, 2, 3, ...
    expected_numbers = list(range(1, len(event_numbers) + 1))
    assert event_numbers == expected_numbers, "Event numbers should be sequential"
