"""Week generation router for calendar events.

SSE streaming endpoint for generating weekly calendar events using LLM.
"""

import json
import logging
from typing import AsyncGenerator
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from integrations.supabase_service import get_supabase
from ..models.generation import WeekGenerationRequest
from ..services.week_generator import generate_week_events_streaming

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Generation"])


def _parse_week_id(week_id: str) -> tuple[int, int]:
    """Parse week_id like '2025-W09' into (year, week_num)."""
    parts = week_id.split("-W")
    if len(parts) != 2:
        raise ValueError(f"Invalid week_id format: {week_id}")
    return int(parts[0]), int(parts[1])


def _get_week_dates(year: int, week_num: int) -> tuple[datetime, datetime]:
    """Get start and end dates for a given ISO week."""
    # ISO week 1 is the first week with Thursday in it
    jan_4 = datetime(year, 1, 4)
    week_1_start = jan_4 - timedelta(days=jan_4.weekday())
    target_week_start = week_1_start + timedelta(weeks=week_num - 1)
    target_week_end = target_week_start + timedelta(days=6)
    return target_week_start, target_week_end


@router.options("/generate-week/{week_id}")
async def options_generate_week(week_id: str):
    """Handle OPTIONS preflight request for CORS."""
    logger.info(f"[GENERATION_ROUTER] OPTIONS preflight request for week {week_id}")
    return {"status": "ok"}


@router.post("/generate-week/{week_id}")
async def generate_week(
    week_id: str,
    request: WeekGenerationRequest,
    user_id: str = "00000000-0000-0000-0000-000000000000",  # TODO: Get from auth with Depends(get_current_user)
):
    """
    Generate calendar events for a week using AI with streaming.

    SSE Event Types:
    - streaming_started: Generation has begun
    - event_ready: New event generated (emitted AS IT HAPPENS)
    - generation_complete: All events generated
    - generation_error: Error occurred

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        request: Generation request with user goals and context
        user_id: User UUID (TODO: from auth)

    Returns:
        SSE stream of generation events
    """
    try:
        logger.info(f"[GENERATION_ROUTER] ========== REQUEST RECEIVED ==========")
        logger.info(f"[GENERATION_ROUTER] Week ID: {week_id}")
        logger.info(f"[GENERATION_ROUTER] User ID: {user_id}")
        logger.info(f"[GENERATION_ROUTER] User goals: {request.user_goals}")
        logger.info(f"[GENERATION_ROUTER] User context: {request.user_context}")
        logger.info(f"[GENERATION_ROUTER] ==========================================")
        logger.info(f"[GENERATION_ROUTER] Starting week generation for {week_id}, user {user_id}")

        # Parse week_id to get date range
        try:
            logger.info(f"[GENERATION_ROUTER] Parsing week_id: {week_id}")
            year, week_num = _parse_week_id(week_id)
            logger.info(f"[GENERATION_ROUTER] Parsed: year={year}, week={week_num}")
            week_start, week_end = _get_week_dates(year, week_num)
            logger.info(f"[GENERATION_ROUTER] Calculated week dates: {week_start.date()} to {week_end.date()}")
        except ValueError as e:
            logger.error(f"[GENERATION_ROUTER] Invalid week_id format: {e}")
            raise HTTPException(status_code=400, detail=str(e))

        logger.info(f"[GENERATION_ROUTER] Week range: {week_start.date()} to {week_end.date()}")

        # Get database client
        db_client = get_supabase()

        # Load existing events for the week if needed
        existing_events = request.existing_events
        if existing_events is None:
            # Fetch existing events from database
            try:
                response = (
                    db_client.table("calendar_events")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("scheduled_date", week_start.date().isoformat())
                    .lte("scheduled_date", week_end.date().isoformat())
                    .order("scheduled_date", desc=False)
                    .execute()
                )
                existing_events = response.data
                logger.info(f"[GENERATION_ROUTER] Loaded {len(existing_events)} existing events")
            except Exception as e:
                logger.warning(f"[GENERATION_ROUTER] Failed to load existing events: {e}")
                existing_events = []

        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from week generation."""
            logger.info(f"[GENERATION_ROUTER] Starting SSE event generator")
            event_count = 0

            try:
                logger.info(f"[GENERATION_ROUTER] Beginning event streaming from generation service...")

                # Stream events from generation service
                async for stream_event in generate_week_events_streaming(
                    week_id=week_id,
                    week_start=week_start,
                    week_end=week_end,
                    user_goals=request.user_goals,
                    user_context=request.user_context,
                    existing_events=existing_events,
                ):
                    event_count += 1
                    event_type = stream_event["event_type"]
                    logger.debug(f"[GENERATION_ROUTER] Stream event #{event_count}: {event_type}")

                    if stream_event["event_type"] == "streaming_started":
                        logger.info(f"[GENERATION_ROUTER] Streaming started: {stream_event.get('message')}")

                    elif stream_event["event_type"] == "event_ready":
                        # Store event in database
                        event_data = stream_event["event_data"]
                        logger.info(f"[GENERATION_ROUTER] Event #{stream_event.get('event_number')} ready: {event_data['title']}")

                        try:
                            # Insert event into calendar_events table
                            insert_data = {
                                "user_id": user_id,
                                "title": event_data["title"],
                                "description": event_data.get("description", ""),
                                "scheduled_date": event_data["scheduled_date"],
                                "start_time": event_data["start_time"],
                                "end_time": event_data["end_time"],
                            }

                            logger.debug(f"[GENERATION_ROUTER] Inserting event to DB: {insert_data['title']}")
                            result = db_client.table("calendar_events").insert(insert_data).execute()

                            if result.data and len(result.data) > 0:
                                event_id = result.data[0]["id"]
                                stream_event["event_id"] = event_id
                                logger.info(
                                    f"💾 [GENERATION_ROUTER] Stored event: {event_data['title']} -> {event_id}"
                                )
                            else:
                                logger.error(f"❌ [GENERATION_ROUTER] Failed to store event: No data returned")

                        except Exception as e:
                            logger.error(f"❌ [GENERATION_ROUTER] Failed to store event in database: {e}")
                            # Continue streaming even if storage fails

                    # Stream the event to client
                    json_data = json.dumps(stream_event)
                    logger.debug(f"[GENERATION_ROUTER] Yielding SSE: {json_data[:100]}...")
                    yield f"data: {json_data}\n\n"

                    if stream_event["event_type"] == "generation_complete":
                        logger.info(
                            f"✅ Week generation completed: {stream_event.get('total_events', 0)} events"
                        )
                        break

                    if stream_event["event_type"] == "generation_error":
                        logger.error(f"❌ Generation error: {stream_event.get('error')}")
                        break

            except Exception as e:
                logger.error(f"[GENERATION_ROUTER] Stream error: {e}", exc_info=True)
                yield f"data: {json.dumps({'event_type': 'generation_error', 'error': str(e)})}\n\n"

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error(f"[GENERATION_ROUTER] Failed to initialize generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
