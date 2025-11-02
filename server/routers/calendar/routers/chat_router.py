"""SSE streaming chat router for calendar agent."""

import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from agents import Runner, RunContextWrapper, RunConfig
from integrations.supabase_service import get_supabase
from ..models import CalendarChatRequest, CalendarContext
from ..services import CalendarContextLoader, CalendarConversationManager
from ..services.openrouter_provider import OPENROUTER_PROVIDER
from ..agents import create_calendar_conversation_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Chat"])


def _pull_immediate_events(
    context_wrapper: RunContextWrapper[CalendarContext],
    emitted_patch_ids: set[str],
) -> list[dict]:
    """Pull immediate SSE events from context and mark as emitted.

    Args:
        context_wrapper: Wrapped CalendarContext
        emitted_patch_ids: Set of patch IDs already emitted (dedupe)

    Returns:
        List of SSE event payloads ready to send
    """
    # Unwrap context
    context = context_wrapper
    guard = 4
    while hasattr(context, "context") and guard:
        context = getattr(context, "context")
        guard -= 1

    # Get immediate events list
    immediate_events = context.agent_outputs.get("immediate_sse_events", [])
    logger.debug(f"[_PULL_IMMEDIATE_EVENTS] Found {len(immediate_events)} events in queue")
    if not immediate_events:
        return []

    # Filter out already-emitted patches
    new_events = []
    for event in immediate_events:
        patch = event.get("patch")
        patch_id = patch.get("patch_id") if patch else None

        # Deduplicate by patch_id
        if patch_id and patch_id in emitted_patch_ids:
            logger.debug(f"[_PULL_IMMEDIATE_EVENTS] Skipping duplicate patch_id: {patch_id}")
            continue

        new_events.append(event)

        if patch_id:
            emitted_patch_ids.add(patch_id)

    logger.debug(f"[_PULL_IMMEDIATE_EVENTS] Returning {len(new_events)} new events (after dedup)")

    # Clear the immediate events queue (already emitted)
    immediate_events.clear()

    return new_events


@router.post("/chat/{week_id}")
async def chat_with_calendar(
    week_id: str,
    request: CalendarChatRequest,
    user_id: str = "00000000-0000-0000-0000-000000000000",  # TODO: Get from auth with Depends(get_current_user)
) -> StreamingResponse:
    """Stream calendar chat responses with real-time patch emission.

    SSE Event Types:
    - patch_proposed: New patch from agent tool (emitted AS IT HAPPENS)
    - final: Complete message + all patches

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        request: Chat request with message and optional conversation_id
        user_id: User UUID (TODO: from auth)

    Returns:
        SSE stream of events
    """
    try:
        logger.info(f"[CHAT_ROUTER] Starting chat for week {week_id}, user {user_id}")

        # Get database client
        db_client = get_supabase()

        # Initialize conversation manager
        conversation_manager = CalendarConversationManager(db_client)
        conversation = conversation_manager.get_or_create_conversation(
            week_id=week_id,
            user_id=user_id,
            conversation_id=request.conversation_id,
        )

        # Load week context
        context_loader = CalendarContextLoader(db_client)
        context_data = context_loader.load_week_context(week_id, user_id)

        # Get conversation history
        history = conversation_manager.get_conversation_context(
            conversation_id=conversation["id"],
            max_turns=10,
        )

        # Create CalendarContext instance (not dict)
        calendar_context = CalendarContext(
            week_id=week_id,
            user_id=user_id,
            week_snapshot=context_data["week_snapshot"],
            event_locators=context_data["event_locators"],
            conversation_history=history,
        )

        # Wrap context for Agents SDK
        context_wrapper = RunContextWrapper(calendar_context)

        # Store model_provider in context for child agents to access
        calendar_context.agent_outputs["model_provider"] = OPENROUTER_PROVIDER
        logger.info("[CHAT_ROUTER] Stored model_provider in context.agent_outputs for child agents")

        logger.info(f"[CHAT_ROUTER] Context loaded, starting streaming agent")

        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from agent execution IN REAL-TIME."""
            logger.info("[CHAT_ROUTER] SSE event generator started")
            try:
                emitted_patch_ids = set()

                # Create conversation agent
                agent = create_calendar_conversation_agent(
                    week_snapshot=calendar_context.week_snapshot,
                    conversation_history=history,
                )
                logger.info("[CHAT_ROUTER] Conversation agent created")

                # Run agent with streaming and OpenRouter provider
                streaming_run = Runner.run_streamed(
                    starting_agent=agent,
                    input=request.message,
                    context=context_wrapper,
                    run_config=RunConfig(model_provider=OPENROUTER_PROVIDER),
                )
                logger.info("[CHAT_ROUTER] Starting to stream agent events")

                # Stream events AS THEY HAPPEN
                async for stream_event in streaming_run.stream_events():
                    # Pull any immediate events that were queued by tools
                    immediate_events = _pull_immediate_events(context_wrapper, emitted_patch_ids)
                    logger.info(f"[CHAT_ROUTER] Pulled {len(immediate_events)} immediate events from context")
                    for payload in immediate_events:
                        logger.info(f"[CHAT_ROUTER] Yielding SSE event: type={payload.get('type')}")
                        yield format_sse(payload)

                # Get final result (available after stream completes)
                final_output = streaming_run.final_output
                logger.info(f"[CHAT_ROUTER] Final output received: {str(final_output)[:100] if final_output else 'None'}")

                # Get all proposed patches
                proposed_patches = calendar_context.agent_outputs.get("proposed_calendar_patches", [])
                logger.info(f"[CHAT_ROUTER] Total patches collected: {len(proposed_patches)}")

                # Final message
                final_message = str(final_output) if final_output else "I've processed your request."

                # Save conversation turn (best effort - don't fail stream if this errors)
                try:
                    conversation_manager.add_conversation_turn(
                        conversation_id=conversation["id"],
                        user_message=request.message,
                        agent_response=final_message,
                        patches=proposed_patches,
                    )
                    logger.info("[CHAT_ROUTER] Conversation turn saved successfully")
                except Exception as e:
                    logger.warning(f"[CHAT_ROUTER] Failed to save conversation turn: {e}")

                # Emit final event
                logger.info(f"[CHAT_ROUTER] Yielding final SSE event with {len(proposed_patches)} patches")
                yield format_sse({
                    "type": "final",
                    "message": final_message,
                    "patches": proposed_patches,
                    "conversation_id": conversation["id"],
                })

                logger.info(f"[CHAT_ROUTER] Stream completed successfully with {len(proposed_patches)} patches")

            except Exception as e:
                logger.error(f"[CHAT_ROUTER] Stream error: {e}", exc_info=True)
                yield format_sse({
                    "type": "error",
                    "message": str(e),
                })

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error(f"[CHAT_ROUTER] Failed to initialize chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def format_sse(payload: dict) -> str:
    """Format payload as SSE event (trainwithai pattern)."""
    return f"data: {json.dumps(payload)}\n\n"
