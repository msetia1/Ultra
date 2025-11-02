"""Pytest configuration and fixtures for calendar integration tests."""

import os
import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from integrations.supabase_service import get_supabase

# Test user ID (matches TEST_USER_ID in app.py)
TEST_USER_ID = "00000000-0000-0000-0000-000000000000"

# Base URL for API server (must be running)
TEST_API_BASE_URL = os.getenv("TEST_API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def test_user_id():
    """Test user ID fixture."""
    return TEST_USER_ID


@pytest.fixture
async def async_client():
    """Async HTTP client for hitting actual running server.

    Note: The FastAPI server must be running before tests execute.
    Start server with: uvicorn app:app --reload --port 8000
    """
    async with AsyncClient(base_url=TEST_API_BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
def supabase_client():
    """Supabase client for database verification."""
    return get_supabase()


@pytest.fixture(scope="session")
def setup_test_user():
    """Create test user in Users table (session-scoped, runs once).

    This is required because calendar_events and calendar_conversations
    have foreign key constraints to Users.id.
    """
    supabase = get_supabase()

    # Try to create test user (ignore if already exists)
    try:
        supabase.table("Users").insert({
            "id": TEST_USER_ID,
            "display_name": "Test User",
            "timezone": "UTC",
        }).execute()
        print(f"✓ Created test user: {TEST_USER_ID}")
    except Exception as e:
        # User might already exist - that's fine
        print(f"✓ Test user already exists: {TEST_USER_ID}")

    yield

    # Optional: Cleanup test user after all tests
    # Commented out to allow debugging between test runs
    # supabase.table("Users").delete().eq("id", TEST_USER_ID).execute()


@pytest.fixture
async def clean_calendar_db(supabase_client, test_user_id, setup_test_user):
    """Clean up calendar data before each test.

    Depends on setup_test_user to ensure foreign key constraints are satisfied.
    """
    # Delete all calendar events for test user
    supabase_client.table("calendar_events").delete().eq("user_id", test_user_id).execute()

    # Delete all conversations for test user
    supabase_client.table("calendar_conversations").delete().eq("user_id", test_user_id).execute()

    yield

    # Cleanup after test
    supabase_client.table("calendar_events").delete().eq("user_id", test_user_id).execute()
    supabase_client.table("calendar_conversations").delete().eq("user_id", test_user_id).execute()


@pytest.fixture
def sample_week_id():
    """Generate a week ID for current week."""
    today = date.today()
    # ISO week: year-Wweek_number
    year, week_num, _ = today.isocalendar()
    return f"{year}-W{week_num:02d}"


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    return {
        "title": "Team Meeting",
        "description": "Weekly sync",
        "date": tomorrow.isoformat(),
        "start_time": "14:00",
        "end_time": "15:00",
    }


@pytest.fixture
async def create_test_event(supabase_client, test_user_id, sample_event_data, setup_test_user):
    """Fixture that creates a test event and returns its ID.

    Depends on setup_test_user to ensure foreign key constraints are satisfied.
    """
    response = (
        supabase_client.table("calendar_events")
        .insert({
            "user_id": test_user_id,
            "title": sample_event_data["title"],
            "description": sample_event_data["description"],
            "scheduled_date": sample_event_data["date"],
            "start_time": sample_event_data["start_time"],
            "end_time": sample_event_data["end_time"],
        })
        .execute()
    )

    event_id = response.data[0]["id"]

    yield event_id

    # Cleanup
    supabase_client.table("calendar_events").delete().eq("id", event_id).execute()
