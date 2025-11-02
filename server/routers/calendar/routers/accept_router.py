"""Accept patches endpoint for persisting calendar changes."""

import logging
from fastapi import APIRouter, HTTPException
from integrations.supabase_service import get_supabase
from ..models import (
    CalendarAcceptRequest,
    CalendarAddEventPatch,
    CalendarRemoveEventPatch,
    CalendarModifyEventPatch,
    CalendarMoveEventPatch,
)
from ..services import CalendarPersistenceService, CalendarConversationManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar Accept"])


@router.post("/accept-patches/{week_id}")
async def accept_calendar_patches(
    week_id: str,
    request: CalendarAcceptRequest,
    user_id: str = "00000000-0000-0000-0000-000000000000",  # TODO: Get from auth with Depends(get_current_user)
) -> dict:
    """Accept and persist calendar patches to database.

    This endpoint:
    1. Validates patches
    2. Applies patches in order (remove/add/move/modify)
    3. Updates database tables
    4. Records acceptance in conversation history

    Args:
        week_id: Week identifier
        request: Accept request with patches and optional conversation_id
        user_id: User UUID

    Returns:
        Dict with status and results
    """
    try:
        logger.info(f"[ACCEPT_ROUTER] Accepting {len(request.patches)} patches for week {week_id}")

        # Parse and validate patches
        patches = _parse_patches(request.patches)

        # Get database client
        db_client = get_supabase()

        # Apply patches to database
        persistence = CalendarPersistenceService(db_client)
        result = persistence.apply_calendar_patches(user_id, patches)

        # Record patch acceptance in conversation if conversation_id provided
        if request.conversation_id:
            conversation_manager = CalendarConversationManager(db_client)
            patch_ids = [p.get("patch_id") for p in request.patches if p.get("patch_id")]
            conversation_manager.record_patch_action(
                conversation_id=request.conversation_id,
                accepted_ids=patch_ids,
            )

        logger.info(f"[ACCEPT_ROUTER] Successfully applied patches: {result}")

        return {
            "status": "ok",
            **result,
        }

    except Exception as e:
        logger.error(f"[ACCEPT_ROUTER] Failed to accept patches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _parse_patches(payloads: list[dict]) -> list:
    """Parse patch payloads into typed patch objects."""
    MODEL_BY_OP = {
        "add_event": CalendarAddEventPatch,
        "remove_event": CalendarRemoveEventPatch,
        "modify_event": CalendarModifyEventPatch,
        "move_event": CalendarMoveEventPatch,
    }

    patches = []
    for payload in payloads:
        op = payload.get("op")
        model = MODEL_BY_OP.get(op)
        if not model:
            raise HTTPException(400, f"Unsupported patch op: {op}")

        try:
            patches.append(model(**payload))
        except Exception as e:
            logger.error(f"[ACCEPT_ROUTER] Invalid patch: {e}", exc_info=True)
            raise HTTPException(400, f"Invalid patch: {e}")

    return patches
