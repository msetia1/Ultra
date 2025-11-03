"""Week event generation service using OpenRouter streaming.

Generates calendar events for a week using LLM with structured output and token-level streaming.
Pattern based on Trayne weekly_generation.py approach.
"""

import os
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from supabase import Client

from ..models.generation import WeekEventsGeneration, CalendarEventGeneration
from .event_streaming_parser import EventStreamingParser
from .user_context_aggregator import UserContextAggregator
from .overlap_validator import OverlapValidator

logger = logging.getLogger(__name__)


async def generate_week_events_streaming(
    week_id: str,
    week_start: datetime,
    week_end: datetime,
    user_id: str,
    supabase_client: Client,
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
        user_id: User's UUID for fetching integration data
        supabase_client: Supabase client for database queries
        user_goals: Optional user goals or focus areas
        user_context: Optional additional context
        existing_events: Optional list of existing events to consider

    Yields:
        Stream events with generated calendar events as they become available
    """
    logger.info(f"🚀 Starting week event generation for {week_id}")
    logger.info(f"📅 Week range: {week_start.date()} to {week_end.date()}")

    # Aggregate user data from GitHub, Whoop, and Linear integrations
    aggregator = UserContextAggregator(supabase_client)
    integration_context = aggregator.aggregate_week_context(
        user_id=user_id,
        week_start=week_start.date(),
        week_end=week_end.date()
    )
    integration_context_text = aggregator.format_context_for_prompt(integration_context)

    logger.info(f"📊 Integration context aggregated: {len(integration_context_text)} characters")
    if integration_context["integration_status"].get("has_github"):
        logger.info("  ✓ GitHub data included")
    if integration_context["integration_status"].get("has_whoop"):
        logger.info("  ✓ Whoop data included")
    if integration_context["integration_status"].get("has_linear"):
        logger.info("  ✓ Linear data included")

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

    # Create comprehensive system prompt with integration context
    system_prompt = f"""You are an AI calendar assistant that generates smart, balanced weekly schedules.

TASK: Create a well-structured weekly calendar with events that help the user achieve their goals while maintaining work-life balance.

TODAY'S DATE: {datetime.now().strftime('%Y-%m-%d')}

WEEK TO SCHEDULE:
- Week ID: {week_id}
- Start Date: {week_start.strftime('%Y-%m-%d (%A)')}
- End Date: {week_end.strftime('%Y-%m-%d (%A)')}

USER GOALS/FOCUS:
{goals_text}{context_text}{existing_events_text}

{integration_context_text}

INSTRUCTIONS:

1. USE THE INTEGRATION DATA ABOVE:
   - **GitHub activity**: Schedule deep work blocks for active projects during historically productive times
   - **Whoop recovery scores**: Adjust daily schedule intensity based on recovery levels
     * High recovery (>67%): Full workload, meetings, intense workouts OK
     * Moderate recovery (34-66%): Balanced schedule, avoid early meetings
     * Low recovery (<34%): Light schedule, prioritize rest and recovery
   - **Whoop sleep data**: Respect sleep patterns when scheduling morning activities
   - **Whoop workouts**: Pre-block exercise at typical workout times to maintain consistency
   - **Linear tasks**: Create focused time blocks for high-priority tasks and upcoming deadlines
   - **Linear deadlines**: Work backward from due dates to schedule preparation time

2. EVENT GENERATION PHASE:
   Create a balanced weekly schedule with:

   a) WORK/PRODUCTIVITY BLOCKS:
      - Deep work sessions (2-4 hours of focused time) for active GitHub projects
      - Time blocks for Linear tasks based on priority and deadlines
      - Meeting blocks (but avoid meeting overload)
      - Administrative/email time
      - Planning and review sessions

   b) PERSONAL WELLNESS:
      - Exercise/movement sessions at typical workout times (from Whoop data)
      - Meal times (breakfast, lunch, dinner)
      - Breaks and rest periods, especially on low recovery days
      - Extra recovery time when Whoop data shows need

   c) LIFE BALANCE:
      - Hobbies or creative time
      - Social activities
      - Personal development
      - Family/relationship time

   d) STRUCTURE:
      - Morning routines (adjusted based on sleep data)
      - Evening wind-down
      - Weekend activities

3. ⚠️ SCHEDULING RULES - ABSOLUTELY CRITICAL - NO EXCEPTIONS ⚠️

   **RULE #0: EVENT COUNT LIMITS**
   ═══════════════════════════════════════════════════════════
   - **MAXIMUM 10 events per day** - DO NOT exceed this limit
   - **MINIMUM 5 events per day** - EVERY day must have at least five events

   Before creating ANY event, count how many events you have already created for that specific day.
   If the day already has 10 events, DO NOT add another event to that day.
   Move to a different day instead.

   Ensure ALL 7 days get at least 5 events before adding more events to any single day.

   Track your count as you generate:
   - Monday: [0/10] → [1/10] → [2/10] → ... → [10/10] STOP
   - Tuesday: [0/10] → [1/10] → [2/10] → ... → [10/10] STOP
   - And so on for all 7 days...

   **RULE #1: ZERO OVERLAPS - THIS IS NON-NEGOTIABLE**
   ═══════════════════════════════════════════════════════════
   FOR ANY GIVEN DAY, EVENTS MUST NEVER OVERLAP IN TIME.
   EVERY EVENT MUST BE COMPLETELY FINISHED BEFORE THE NEXT ONE STARTS.

   ❌ OVERLAPPING IS ABSOLUTELY FORBIDDEN ❌

   How to ensure NO overlaps:

   Step 1: Keep a mental list of ALL events you've already created for EACH day
   Step 2: Before creating a new event, CHECK the list for that specific day
   Step 3: Find a time slot that comes AFTER all existing events (or BEFORE all of them)
   Step 4: Add AT LEAST 15 minutes buffer between the end of one event and start of next

   **RULE #1.5: SPREAD EVENTS THROUGHOUT EACH DAY - CRITICAL**
   ═══════════════════════════════════════════════════════════
   ⚠️ DO NOT CLUSTER ALL EVENTS IN ONE PART OF THE DAY ⚠️

   Events MUST be distributed across the full day when possible:
   - **Morning**: 06:00-12:00 (early activities, morning routines, deep work)
   - **Afternoon**: 12:00-17:00 (meetings, collaborative work, lunch, mid-day activities)
   - **Evening**: 17:00-23:00 (exercise, personal time, wind-down)

   **DISTRIBUTION STRATEGY:**
   - For days with 5-7 events: Spread across morning, mid-day, afternoon, and evening
   - For days with 8-10 events: Fill the entire day from morning to evening with varied activities
   - Include short events (15-30 min breaks, meals) and longer events (1-3 hour work blocks)
   - Avoid clustering all events in a single time period
   - Space events with meaningful gaps (15-60 minutes) between them when possible
   - Mix event types throughout the day (work, breaks, meals, exercise, personal)

   **VALID EXAMPLE for Monday (8 events, well-distributed):**
   ✓ Event 1: 07:00-07:30 (Morning Routine) ← EARLY MORNING
   ✓ Event 2: 08:00-10:00 (Deep Work - GitHub Project) ← MORNING
   ✓ Event 3: 10:15-10:30 (Coffee Break) ← MORNING
   ✓ Event 4: 11:00-12:30 (Team Standup & Planning) ← LATE MORNING
   ✓ Event 5: 12:30-13:30 (Lunch Break) ← MID-DAY
   ✓ Event 6: 14:00-16:00 (Deep Work - Linear Task) ← AFTERNOON
   ✓ Event 7: 16:30-17:00 (Email & Admin) ← LATE AFTERNOON
   ✓ Event 8: 18:00-19:30 (Exercise & Recovery) ← EVENING

   Perfect distribution: Events span from 7 AM to 7:30 PM with varied durations and good spacing!

   **INVALID EXAMPLE (DO NOT CLUSTER LIKE THIS):**
   ❌ Event 1: 09:00-10:00 (Deep Work)
   ❌ Event 2: 10:15-11:00 (Meeting) ← TOO CLOSE, CLUSTERED
   ❌ Event 3: 11:15-12:00 (Review) ← TOO CLOSE, CLUSTERED
   ❌ Event 4: 12:30-13:00 (Lunch) ← ALL EVENTS IN ONE MORNING WINDOW

   This is wrong! All events happen in 4 hours (9 AM - 1 PM), leaving the rest of the day empty.
   Spread them out across morning, afternoon, and evening instead!

   INVALID EXAMPLE (DO NOT DO THIS):
   ❌ Event 1: 09:00-12:00 (Deep Work)
   ❌ Event 2: 10:00-11:00 (Meeting) ← WRONG! Overlaps with Event 1
   ❌ Event 3: 11:30-12:30 (Exercise) ← WRONG! Overlaps with Event 1
   ❌ Event 4: 12:00-13:00 (Lunch) ← WRONG! Overlaps with Events 1 and 3
   ❌ Event 11: 14:00-15:00 (Review) ← WRONG! 11 events in one day (max is 10)

   **WHY THIS MATTERS:**
   You can only do ONE thing at a time. It is physically impossible to be in a meeting
   while also doing deep work. All events must be sequential, never concurrent.

   **DATE VALIDATION:**
   - All events MUST have scheduled_date within [{week_start.strftime('%Y-%m-%d')}, {week_end.strftime('%Y-%m-%d')}]
   - Use realistic times (not before 06:00, not after 23:00)

   **BUFFER REQUIREMENTS:**
   - MINIMUM 15 minutes between consecutive events on same day
   - More buffer is better (30-60 minutes for transitions between different types of activities)

   **OTHER RULES:**
   - Balance busy days with lighter days based on recovery scores
   - Respect typical work hours (9am-6pm for work, flexible for personal)
   - Schedule demanding work during high-energy periods
   - Add buffer time before Linear task deadlines
   - **CRITICAL: Spread events across full day** - Don't cluster all events in morning or afternoon
   - **Use time gaps strategically** - Space events 1-3 hours apart to allow for natural transitions
   - **Distribute across time zones** - Morning activities, afternoon work, evening wellness/personal

4. EVENT DETAILS:
   Each event must include:
   - title: Clear, descriptive title
   - description: **RICH, COMPREHENSIVE DESCRIPTION (4-6 sentences)** - See detailed guidance below
   - scheduled_date: Date in YYYY-MM-DD format
   - start_time: Time in HH:MM format (24-hour)
   - end_time: Time in HH:MM format (24-hour)
   - event_type: Type of event (e.g., "work", "exercise", "personal", "meal", "social")
   - priority: "high", "medium", or "low"

   **DESCRIPTION QUALITY GUIDELINES:**
   ═══════════════════════════════════════════════════════════════════════════
   Descriptions are CRITICAL for user context. They should be RICH, INSIGHTFUL narratives
   that explain WHY this event is scheduled at this specific time, using patterns and context
   from the integration data above.

   **Core Principles for Descriptions:**

   1. **EXPLAIN THE "WHY"**: Don't just state what the event is - explain WHY it's scheduled
      at this time and date. Reference the reasoning behind the scheduling decision.

   2. **REFERENCE PATTERNS, NOT RAW DATA**: Instead of "Your recovery score is 78%", say:
      - "Based on your high recovery score today, you have excellent energy for intense work"
      - "Historically you're most productive in morning hours based on your commit patterns"
      - "Scheduled at your typical workout time to maintain consistency with your routine"

   3. **COMBINE MULTIPLE DATA SOURCES**: Weave together insights from GitHub, Whoop, and Linear:
      - GitHub activity patterns + Whoop recovery scores + timing
      - Linear task priorities + GitHub project context + energy levels
      - Whoop workout patterns + recovery trends + schedule balance

   4. **FOCUS ON INSIGHTS OVER SPECIFICS**: Avoid technical details users won't recognize:
      - ❌ BAD: "Complete task ENG-456 in Linear with ID abc-123-xyz"
      - ✅ GOOD: "Focus time for high-priority API integration task due in 3 days"
      - ❌ BAD: "Work on repo github.com/user/project-name-12345"
      - ✅ GOOD: "Continue work on the calendar generation backend you've been iterating on"

   5. **KEEP IT CONVERSATIONAL**: Write naturally, as if explaining the schedule to the user:
      - Use "you/your" language
      - Be specific but accessible
      - Highlight relevant context that matters to the user

   6. **LENGTH**: 4-6 sentences that provide comprehensive context without overwhelming detail

   **DESCRIPTION EXAMPLES BY EVENT TYPE:**

   **WORK/DEEP WORK EVENTS:**
   Example 1: "Deep work block scheduled for 9 AM when your recovery score indicates peak
   energy levels. Based on your GitHub activity, you've been actively committing to the
   backend services project with 15+ commits this week. Historically, your commit patterns
   show you're most productive during morning hours. This 3-hour block protects focused
   time for the calendar generation improvements you've been iterating on. No meetings
   scheduled during this window to maintain flow state."

   Example 2: "Focused coding session aligned with your recent work on the authentication
   system based on commit history. Scheduled mid-morning when you typically show strong
   productivity patterns. Your current recovery level supports sustained concentration work.
   This block leaves buffer time before afternoon meetings and aligns with your natural
   work rhythm. Project momentum suggests this is a good time to push forward on pending
   features."

   **EXERCISE/WELLNESS EVENTS:**
   Example 1: "Evening cardio session scheduled at 5 PM, which aligns with your typical
   workout time based on Whoop activity data. Your current recovery level of 82% supports
   moderate to high-intensity exercise. Historically, you maintain a consistent 5x/week
   running cadence, and this session helps preserve that pattern. Evening workouts fit well
   with your schedule and support good sleep quality. Post-workout recovery window extends
   into your evening wind-down routine."

   Example 2: "Morning yoga and mobility work scheduled during a moderate recovery day to
   support active recovery. Based on your Whoop sleep data, you typically wake naturally
   around this time. Light movement in the morning helps prepare you for the workday ahead
   without overtaxing your system. This session is positioned before your deep work block
   to energize and focus your mind. Recovery-focused exercise is appropriate given today's
   moderate HRV readings."

   **TASK/PROJECT EVENTS:**
   Example 1: "Dedicated time for high-priority infrastructure task due in 3 days. Scheduled
   during your peak productivity hours with strong recovery metrics supporting complex problem-
   solving work. This task connects to your recent backend development work visible in GitHub
   activity. The 2-hour block provides enough time for meaningful progress without context-
   switching fatigue. Positioned with buffer time before and after to avoid scheduling conflicts."

   Example 2: "Focus block for urgent API integration work approaching deadline. Based on task
   complexity and your coding patterns, a 3-hour session will allow you to complete core
   implementation. Scheduled when your energy levels are high and calendar is clear of meetings.
   This work builds on the services layer you've been developing recently. Strategic timing
   ensures you can review and test before end of week deadline."

   **MEAL/BREAK EVENTS:**
   Example: "Lunch break positioned between morning deep work and afternoon meetings. Scheduled
   during natural mid-day energy dip to align with circadian rhythm. This break provides recovery
   time after intensive morning productivity session. One-hour duration allows for proper meal
   and mental reset before afternoon activities. Strategic placement maintains sustainable daily
   work rhythm."

   **SOCIAL/PERSONAL EVENTS:**
   Example: "Personal time scheduled on a lighter day to maintain work-life balance. Based on
   your weekly patterns, this provides needed variety after several intensive work days. Current
   recovery metrics support social engagement without overcommitting energy. Weekend positioning
   allows for relaxation without impacting weekday productivity blocks. This balance helps
   sustain long-term performance and wellness."

   **KEY REMINDERS:**
   - Every description should answer: "Why is this event scheduled at THIS specific time?"
   - Reference user patterns: "Based on your...", "Historically you...", "Your typical..."
   - Connect to integration data: GitHub activity, Whoop metrics, Linear priorities, timing patterns
   - Use conversational, accessible language - avoid technical IDs or overwhelming specifics
   - Aim for 4-6 sentences that feel informative and personalized, not generic

5. EVENT COUNT AND QUALITY STANDARDS:

   **EVENT COUNT REQUIREMENTS**
   ═══════════════════════════════════════════════════════════
   - **MAXIMUM 10 events per day** - NO EXCEPTIONS
   - **MINIMUM 5 events per day** - EVERY day must be covered
   - **Total for the week: 35-70 events** (5-10 events/day × 7 days)
   - Create a FULL, REALISTIC daily schedule with varied activities
   - Mix short events (15-30 min breaks, meals) with longer events (1-3 hour work blocks)

   **EVENT DISTRIBUTION:**
   - Spread events across all 7 days of the week
   - **First priority**: Ensure every day has at least 5 events
   - **Second priority**: Add additional events (up to 10) to create comprehensive daily schedules
   - Weekends should have 5-7 events (lighter but structured), weekdays typically 7-10 events
   - **Temporal distribution**: For each day, spread events across morning (06:00-12:00), afternoon (12:00-17:00), and evening (17:00-23:00)
   - Avoid clustering: Don't put all events for a day in a single time period

   **QUALITY AND VARIETY:**
   - Each event should be significant and purposeful
   - Ensure variety in event types across the week
   - Include realistic time durations (15 min breaks to 3 hour work blocks)
   - Include daily essentials: meals, breaks, exercise, work, personal time
   - Add helpful descriptions that explain the purpose
   - Consider energy levels throughout the day
   - Balance structure with flexibility

6. FINAL VALIDATION BEFORE RETURNING:
   ⚠️ BEFORE YOU RETURN THE JSON, DO THIS FINAL CHECK:

   For EACH day in the week:
   a) Count events for that day - MUST BE between 5 and 10 (inclusive)
   b) List all events for that day sorted by start_time
   c) Verify each event ENDS before the next event STARTS
   d) Verify at least 15 minutes between consecutive events
   e) **Check temporal distribution**: Ensure events are spread across the day, not clustered
      - For 5-7 events: Should span morning, afternoon, and evening with varied spacing
      - For 8-10 events: Should fill the entire day from early morning to evening
      - Events should include mix of short (15-30 min) and long (1-3 hour) durations
      - If all events fit in a single 4-hour window, REDISTRIBUTE them across the day
   f) If ANY day has <5 events, ADD more events to reach minimum of 5
   g) If ANY day has >10 events, REMOVE the least important ones
   h) If ANY overlap found, FIX IT by adjusting times or removing events
   i) If events are clustered in one part of the day, REDISTRIBUTE them

   ONLY return the JSON after confirming:
   - ZERO overlaps exist
   - EVERY day has 5-10 events (no day has fewer than 5, no day exceeds 10)
   - Events are distributed across the full day (not all clustered in one time period)
   - Mix of event types and durations throughout each day

STRICT JSON OUTPUT:
Return a single JSON object exactly of the form:
{{"events": [ ... ]}}
with each event conforming to the structure above. No prose before or after the JSON.
"""

    try:
        # Initialize OpenRouter client and validator
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            timeout=None
        )
        parser = EventStreamingParser()
        validator = OverlapValidator(min_buffer_minutes=15)
        emitted_events = []  # Track emitted events for incremental validation

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

                                # Validate event against previously emitted events on same day
                                event_dict = event.model_dump()
                                same_day_events = [
                                    e for e in emitted_events
                                    if e.get("scheduled_date") == event_dict.get("scheduled_date")
                                ]

                                if same_day_events:
                                    # Validate this event against events from same day
                                    events_to_validate = same_day_events + [event_dict]
                                    validated_events, stats = validator.validate_and_fix_events(
                                        events_to_validate,
                                        max_events_per_day=10
                                    )

                                    # Get the validated version of the current event (last one)
                                    event_dict = validated_events[-1]

                                    if stats.get("events_fixed", 0) > 0:
                                        logger.info(f"🔧 Event {event_count} adjusted to avoid overlap")
                                    if stats.get("events_removed", 0) > 0:
                                        logger.info(f"🗑️ Event {event_count}: {stats['events_removed']} events removed (max 3/day)")

                                # Track this event for future validations
                                emitted_events.append(event_dict)

                                logger.info(f"🔥 Event {event_count} ready: {event_dict['title']}")

                                yield {
                                    "event_type": "event_ready",
                                    "event_number": event_count,
                                    "event_data": event_dict,
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

                                        # Validate event against previously emitted events on same day
                                        event_dict = event.model_dump()
                                        same_day_events = [
                                            e for e in emitted_events
                                            if e.get("scheduled_date") == event_dict.get("scheduled_date")
                                        ]

                                        if same_day_events:
                                            # Validate this event against events from same day
                                            events_to_validate = same_day_events + [event_dict]
                                            validated_events, stats = validator.validate_and_fix_events(
                                                events_to_validate,
                                                max_events_per_day=10
                                            )

                                            # Get the validated version of the current event (last one)
                                            event_dict = validated_events[-1]

                                            if stats.get("events_fixed", 0) > 0:
                                                logger.info(f"🔧 Final event {event_count} adjusted to avoid overlap")
                                            if stats.get("events_removed", 0) > 0:
                                                logger.info(f"🗑️ Final event {event_count}: {stats['events_removed']} events removed (max 3/day)")

                                        # Track this event for future validations
                                        emitted_events.append(event_dict)

                                        yield {
                                            "event_type": "event_ready",
                                            "event_number": event_count,
                                            "event_data": event_dict,
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
