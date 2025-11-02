"""SSE streaming chat router for calendar agent."""

import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from integrations.supabase_service import get_supabase
from ..models import CalendarChatRequest
from ..services import CalendarContextLoader, CalendarConversationManager
from ..agents import run_conversation_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Chat"])


@router.post("/chat/{week_id}")
async def chat_with_calendar(
    week_id: str,
    request: CalendarChatRequest,
    user_id: str = "00000000-0000-0000-0000-000000000000",  # TODO: Get from auth
) -> EventSourceResponse:
    """Stream calendar chat responses with real-time patch emission.

    SSE Event Types:
    - patch_proposed: New patch from agent tool
    - message_delta: Streaming text response
    - final: Complete message + all patches

    Args:
        week_id: Week identifier (e.g., "2025-W09")
        request: Chat request with message and optional conversation_id
        user_id: User UUID (from auth, using TEST_USER_ID for now)

    Returns:
        SSE stream of events
    """
    try:
        logger.info(f"[CHAT_ROUTER] Starting chat for week {week_id}, user {user_id}")

        # Get database client
        db_client = get_supabase()

        # Initialize conversation manager
        conversation_manager = CalendarConversationManager(db_client)
        conversation = await conversation_manager.get_or_create_conversation(
            week_id=week_id,
            user_id=user_id,
            conversation_id=request.conversation_id,
        )

        # Load week context
        context_loader = CalendarContextLoader(db_client)
        context = await context_loader.load_week_context(week_id, user_id)

        # Get conversation history
        history = await conversation_manager.get_conversation_context(
            conversation_id=conversation["id"],
            max_turns=10,
        )
        context["conversation_history"] = history

        logger.info(f"[CHAT_ROUTER] Context loaded, running conversation agent")

        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from agent execution."""
            try:
                # Pull immediate events that were queued during agent execution
                emitted_patch_ids = set()

                # Run conversation agent
                result = await run_conversation_agent(context, request.message)

                # Emit any patches that were queued
                immediate_events = context["agent_outputs"].get("immediate_sse_events", [])
                for event in immediate_events:
                    patch = event.get("patch")
                    patch_id = patch.get("patch_id") if patch else None

                    # Deduplicate by patch_id
                    if patch_id and patch_id in emitted_patch_ids:
                        continue
                    if patch_id:
                        emitted_patch_ids.add(patch_id)

                    yield format_sse(event)

                # Get final message and patches
                final_message = result.get("final_message", "")
                proposed_patches = context["agent_outputs"].get("proposed_calendar_patches", [])

                # Save conversation turn
                await conversation_manager.add_conversation_turn(
                    conversation_id=conversation["id"],
                    user_message=request.message,
                    agent_response=final_message,
                    patches=proposed_patches,
                )

                # Emit final event
                yield format_sse({
                    "type": "final",
                    "message": final_message,
                    "patches": proposed_patches,
                    "conversation_id": conversation["id"],
                })

                logger.info(f"[CHAT_ROUTER] Stream completed with {len(proposed_patches)} patches")

            except Exception as e:
                logger.error(f"[CHAT_ROUTER] Stream error: {e}", exc_info=True)
                yield format_sse({
                    "type": "error",
                    "message": str(e),
                })

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
        logger.error(f"[CHAT_ROUTER] Failed to initialize chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def format_sse(payload: dict) -> str:
    """Format payload as SSE event."""
    return f"data: {json.dumps(payload)}\n\n"
