"""Week event generation service using OpenRouter streaming.

Generates calendar events for a week using LLM with structured output and token-level streaming.
Pattern based on Trayne weekly_generation.py approach.
"""

import os
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, timedelta
from openai import AsyncOpenAI

from ..models.generation import WeekEventsGeneration, CalendarEventGeneration
from .event_streaming_parser import EventStreamingParser

logger = logging.getLogger(__name__)


async def generate_week_events_streaming(
    week_id: str,
    week_start: datetime,
    week_end: datetime,
    user_goals: Optional[str] = None,
    user_context: Optional[Dict[str, Any]] = None,
    existing_events: Optional[List[Dict[str, Any]]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Generate calendar events for a week using streaming LLM with structured output.

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        week_start: Start date of the week
        week_end: End date of the week
        user_goals: Optional user goals or focus areas
        user_context: Optional additional context
        existing_events: Optional list of existing events to consider

    Yields:
        Stream events with generated calendar events as they become available
    """
    logger.info(f"🚀 Starting week event generation for {week_id}")
    logger.info(f"📅 Week range: {week_start.date()} to {week_end.date()}")

    # Build user context string
    goals_text = user_goals or "general productivity and work-life balance"
    context_text = ""
    if user_context:
        context_items = [f"- {k}: {v}" for k, v in user_context.items()]
        context_text = f"\n\nADDITIONAL CONTEXT:\n" + "\n".join(context_items)

    # Build existing events context
    existing_events_text = ""
    if existing_events:
        events_list = []
        for event in existing_events:
            events_list.append(
                f"- {event.get('scheduled_date')} {event.get('start_time')}-{event.get('end_time')}: {event.get('title')}"
            )
        existing_events_text = f"\n\nEXISTING EVENTS TO CONSIDER:\n" + "\n".join(events_list)

    # Create comprehensive system prompt
    system_prompt = f"""You are an AI calendar assistant that generates smart, balanced weekly schedules.

TASK: Create a well-structured weekly calendar with events that help the user achieve their goals while maintaining work-life balance.

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

WEEK TO SCHEDULE:
- Week ID: {week_id}
- Start Date: {week_start.strftime('%Y-%m-%d (%A)')}
- End Date: {week_end.strftime('%Y-%m-%d (%A)')}

USER GOALS/FOCUS:
{goals_text}{context_text}{existing_events_text}

INSTRUCTIONS:

1. RESEARCH PHASE:
   Use web search to research:
   - Best practices for weekly scheduling and time management
   - Optimal times for different types of activities (meetings, deep work, exercise, etc.)
   - Work-life balance strategies
   - Time blocking techniques
   - Productivity patterns based on the user's goals

2. EVENT GENERATION PHASE:
   Create a balanced weekly schedule with:

   a) WORK/PRODUCTIVITY BLOCKS:
      - Deep work sessions (2-4 hours of focused time)
      - Meeting blocks (but avoid meeting overload)
      - Administrative/email time
      - Planning and review sessions

   b) PERSONAL WELLNESS:
      - Exercise/movement sessions (3-5 per week)
      - Meal times (breakfast, lunch, dinner)
      - Breaks and rest periods

   c) LIFE BALANCE:
      - Hobbies or creative time
      - Social activities
      - Personal development
      - Family/relationship time

   d) STRUCTURE:
      - Morning routines
      - Evening wind-down
      - Weekend activities

3. SCHEDULING RULES (STRICT):
   - All events MUST have scheduled_date within [{week_start.strftime('%Y-%m-%d')}, {week_end.strftime('%Y-%m-%d')}]
   - Use realistic times (avoid scheduling too early or too late)
   - Consider existing events and avoid conflicts
   - Balance busy days with lighter days
   - Include buffer time between events
   - Respect typical work hours (9am-6pm for work, flexible for personal)

4. EVENT DETAILS:
   Each event must include:
   - title: Clear, descriptive title
   - description: Purpose and any relevant details (2-3 sentences)
   - scheduled_date: Date in YYYY-MM-DD format
   - start_time: Time in HH:MM format (24-hour)
   - end_time: Time in HH:MM format (24-hour)
   - event_type: Type of event (e.g., "work", "exercise", "personal", "meal", "social")
   - priority: "high", "medium", or "low"

5. QUALITY STANDARDS:
   - Create 15-25 events for the week (not too sparse, not overwhelming)
   - Ensure variety in event types
   - Include realistic time durations
   - Add helpful descriptions that explain the purpose
   - Consider energy levels throughout the day
   - Balance structure with flexibility

STRICT JSON OUTPUT:
Return a single JSON object exactly of the form:
{{"events": [ ... ]}}
with each event conforming to the structure above. No prose before or after the JSON.
"""

    try:
        # Initialize OpenRouter client
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            timeout=None
        )
        parser = EventStreamingParser()

        logger.info(f"🚀 Starting LLM call with web search capability")
        logger.info(f"📝 System prompt: {len(system_prompt)} characters")

        # Yield initial progress event
        yield {
            "event_type": "streaming_started",
            "message": "Generating weekly events...",
            "progress": 10
        }

        # Use streaming API with web search capability
        try:
            stream = await client.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a balanced weekly schedule focused on {goals_text}. Include work, wellness, and personal time."}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "week_events",
                        "schema": WeekEventsGeneration.model_json_schema(),
                        "strict": True
                    }
                },
                stream=True,
                extra_body={
                    "provider": {
                        "sort": "throughput"
                    },
                    # "plugins": [
                    #     {
                    #         "id": "web",
                    #         "max_results": 10
                    #     }
                    # ]
                }
            )

            logger.info(f"🔍 Stream created successfully")

            event_count = 0
            delta_count = 0

            async for chunk in stream:
                # Standard OpenAI chat completions streaming format
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]

                    # Get delta content
                    if choice.delta and choice.delta.content:
                        delta_content = choice.delta.content
                        delta_count += 1

                        if delta_count <= 5 or delta_count % 20 == 0:
                            logger.debug(f"📥 Content Delta #{delta_count}: {repr(delta_content[:100])}...")

                        # Parse events from accumulated JSON
                        new_fields = parser.add_delta(delta_content)

                        if new_fields and "new_events" in new_fields:
                            # Emit events for each newly completed event
                            for i, event_data in enumerate(new_fields["new_events"]):
                                event_index = new_fields["event_indices"][i]
                                event_count += 1

                                # Convert dict to Pydantic model
                                try:
                                    event = CalendarEventGeneration(**event_data)
                                except Exception as e:
                                    logger.error(f"Failed to parse event {event_index}: {e}")
                                    continue

                                logger.info(f"🔥 Event {event_count} ready: {event.title}")

                                yield {
                                    "event_type": "event_ready",
                                    "event_number": event_count,
                                    "event_data": event.model_dump(),
                                    "is_first_event": event_count == 1,
                                    "progress": 10 + min(event_count * 3, 80)
                                }

                    # Check if stream is done
                    if choice.finish_reason:
                        logger.info(f"🏁 Streaming completed with reason: {choice.finish_reason}")
                        logger.info(f"📊 Streaming stats: {delta_count} deltas, {event_count} events")

                        # Check for any remaining unparsed events
                        final_state = parser.get_current_state()
                        if final_state.get("events"):
                            remaining_events = final_state["events"][event_count:]
                            if remaining_events:
                                logger.info(f"🔍 Found {len(remaining_events)} additional events in final parse")
                                for event_data in remaining_events:
                                    try:
                                        event = CalendarEventGeneration(**event_data)
                                        event_count += 1
                                        yield {
                                            "event_type": "event_ready",
                                            "event_number": event_count,
                                            "event_data": event.model_dump(),
                                            "is_first_event": event_count == 1,
                                            "progress": 10 + min(event_count * 3, 80)
                                        }
                                    except Exception as e:
                                        logger.error(f"Failed to parse final event: {e}")

                        break

            # Final yield if stream completed
            yield {
                "event_type": "generation_complete",
                "total_events": event_count,
                "progress": 100
            }

        except Exception as api_error:
            logger.error(f"❌ API CALL FAILED: {api_error}")
            logger.error(f"❌ API Error type: {type(api_error)}")
            if 'event_count' in locals() and event_count > 0:
                logger.warning("⚠️ API error after some events streamed; emitting completion")
                yield {
                    "event_type": "generation_complete",
                    "total_events": event_count,
                    "progress": 100,
                    "warning": f"API call failed after partial success: {str(api_error)}"
                }
            else:
                yield {
                    "event_type": "generation_error",
                    "error": f"API call failed: {str(api_error)}"
                }

    except Exception as e:
        logger.error(f"Error in event streaming: {e}", exc_info=True)
        yield {
            "event_type": "generation_error",
            "error": str(e)
        }
        raise
