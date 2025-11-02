"""Persistence service for applying calendar patches to database."""

import logging
from typing import List, Dict, Any
from supabase import Client
from ..models import (
    CalendarPatch,
    CalendarAddEventPatch,
    CalendarRemoveEventPatch,
    CalendarModifyEventPatch,
    CalendarMoveEventPatch,
)

logger = logging.getLogger(__name__)


class CalendarPersistenceService:
    """Applies calendar patches to database."""

    def __init__(self, db_client: Client):
        self.db = db_client

    def apply_calendar_patches(
        self,
        user_id: str,
        patches: List[CalendarPatch],
    ) -> Dict[str, Any]:
        """Apply patches to calendar_events table.

        Patch application order:
        1. Remove events (clear space)
        2. Add events (create new)
        3. Move events (relocate)
        4. Modify events (update fields)

        Args:
            user_id: User UUID
            patches: List of typed patch objects

        Returns:
            Dict with counts of added/removed/modified/moved events
        """
        try:
            logger.info(f"[PERSISTENCE] Applying {len(patches)} patches for user {user_id}")

            results = {
                "added": [],
                "removed": [],
                "modified": [],
                "moved": [],
            }

            # Group patches by operation
            remove_patches = [p for p in patches if isinstance(p, CalendarRemoveEventPatch)]
            add_patches = [p for p in patches if isinstance(p, CalendarAddEventPatch)]
            move_patches = [p for p in patches if isinstance(p, CalendarMoveEventPatch)]
            modify_patches = [p for p in patches if isinstance(p, CalendarModifyEventPatch)]

            # 1. Remove events
            for patch in remove_patches:
                event_id = self._apply_remove(patch, user_id)
                results["removed"].append(event_id)

            # 2. Add events
            for patch in add_patches:
                event_id = self._apply_add(patch, user_id)
                results["added"].append(event_id)

            # 3. Move events
            for patch in move_patches:
                self._apply_move(patch, user_id)
                results["moved"].append(patch.event_id)

            # 4. Modify events
            for patch in modify_patches:
                self._apply_modify(patch, user_id)
                results["modified"].append(patch.event_id)

            logger.info(
                f"[PERSISTENCE] Applied patches: "
                f"{len(results['added'])} added, "
                f"{len(results['removed'])} removed, "
                f"{len(results['modified'])} modified, "
                f"{len(results['moved'])} moved"
            )

            return results

        except Exception as e:
            logger.error(f"[PERSISTENCE] Failed to apply patches: {e}", exc_info=True)
            raise

    def _apply_add(self, patch: CalendarAddEventPatch, user_id: str) -> str:
        """Insert new event into calendar_events table."""
        event = patch.complete_event

        response = (
            self.db.table("calendar_events")
            .insert({
                "user_id": user_id,
                "title": event.title,
                "description": event.description,
                "scheduled_date": event.date,
                "start_time": event.start_time,
                "end_time": event.end_time,
            })
            .execute()
        )

        event_id = response.data[0]["id"]
        logger.info(f"[PERSISTENCE] Added event {event_id}: {event.title}")
        return event_id

    def _apply_remove(self, patch: CalendarRemoveEventPatch, user_id: str) -> str:
        """Delete event from calendar_events table."""
        self.db.table("calendar_events").delete().eq("id", patch.event_id).eq("user_id", user_id).execute()

        logger.info(f"[PERSISTENCE] Removed event {patch.event_id}")
        return patch.event_id

    def _apply_modify(self, patch: CalendarModifyEventPatch, user_id: str) -> None:
        """Update event fields in calendar_events table."""
        updates = {}

        # Build updates dict from field patches
        for field_patch in patch.field_patches:
            updates[field_patch.field] = field_patch.to_value

        if updates:
            self.db.table("calendar_events").update(updates).eq("id", patch.event_id).eq("user_id", user_id).execute()

            logger.info(f"[PERSISTENCE] Modified event {patch.event_id}: {list(updates.keys())}")

    def _apply_move(self, patch: CalendarMoveEventPatch, user_id: str) -> None:
        """Move event to different date."""
        updates = {
            "scheduled_date": patch.to_day.scheduled_date.isoformat(),
        }

        # Apply post-move time adjustments if any
        if patch.post_move_adjustments:
            for field_patch in patch.post_move_adjustments:
                updates[field_patch.field] = field_patch.to_value

        self.db.table("calendar_events").update(updates).eq("id", patch.event_id).eq("user_id", user_id).execute()

        logger.info(f"[PERSISTENCE] Moved event {patch.event_id} to {patch.to_day.scheduled_date}")
