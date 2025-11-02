"""Conversation manager for calendar chat history."""

import logging
from typing import Dict, Any, List, Optional
from supabase import Client

logger = logging.getLogger(__name__)


class CalendarConversationManager:
    """Manages calendar conversation persistence and retrieval."""

    def __init__(self, db_client: Client):
        self.db = db_client

    def get_or_create_conversation(
        self,
        week_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get existing conversation or create new one.

        Args:
            week_id: Week identifier
            user_id: User UUID
            conversation_id: Optional existing conversation ID

        Returns:
            Conversation record
        """
        try:
            if conversation_id:
                # Fetch existing conversation
                response = (
                    self.db.table("calendar_conversations")
                    .select("*")
                    .eq("id", conversation_id)
                    .eq("user_id", user_id)
                    .single()
                    .execute()
                )
                if response.data:
                    logger.info(f"[CONVERSATION_MANAGER] Using existing conversation {conversation_id}")
                    return response.data

            # Create new conversation
            response = (
                self.db.table("calendar_conversations")
                .insert({
                    "user_id": user_id,
                    "week_id": week_id,
                })
                .execute()
            )

            conversation = response.data[0]
            logger.info(f"[CONVERSATION_MANAGER] Created new conversation {conversation['id']}")
            return conversation

        except Exception as e:
            logger.error(f"[CONVERSATION_MANAGER] Failed to get/create conversation: {e}", exc_info=True)
            raise

    def get_conversation_context(
        self,
        conversation_id: str,
        max_turns: int = 10,
    ) -> str:
        """Get formatted conversation history for agent context.

        Args:
            conversation_id: Conversation UUID
            max_turns: Maximum number of recent turns to include

        Returns:
            Formatted conversation string
        """
        try:
            # Fetch recent turns
            response = (
                self.db.table("calendar_conversation_turns")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(max_turns)
                .execute()
            )

            turns = list(reversed(response.data))  # Oldest first

            if not turns:
                return "(no prior conversation)"

            # Format turns
            formatted = []
            for turn in turns:
                formatted.append(f"User: {turn['user_message']}")
                formatted.append(f"Assistant: {turn['agent_response']}")
                if turn.get("accepted_patch_ids"):
                    formatted.append(f"  (User accepted {len(turn['accepted_patch_ids'])} patches)")

            return "\n".join(formatted)

        except Exception as e:
            logger.error(f"[CONVERSATION_MANAGER] Failed to load context: {e}", exc_info=True)
            return "(error loading conversation history)"

    def add_conversation_turn(
        self,
        conversation_id: str,
        user_message: str,
        agent_response: str,
        patches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Add a new conversation turn.

        Args:
            conversation_id: Conversation UUID
            user_message: User's message
            agent_response: Agent's response
            patches: List of proposed patches

        Returns:
            Created turn record
        """
        try:
            response = (
                self.db.table("calendar_conversation_turns")
                .insert({
                    "conversation_id": conversation_id,
                    "user_message": user_message,
                    "agent_response": agent_response,
                    "patches": patches,
                })
                .execute()
            )

            turn = response.data[0]
            logger.info(f"[CONVERSATION_MANAGER] Added turn {turn['id']}")
            return turn

        except Exception as e:
            logger.error(f"[CONVERSATION_MANAGER] Failed to add turn: {e}", exc_info=True)
            raise

    def record_patch_action(
        self,
        conversation_id: str,
        accepted_ids: List[str] = None,
        rejected_ids: List[str] = None,
    ) -> None:
        """Record patch acceptance/rejection on most recent turn.

        Args:
            conversation_id: Conversation UUID
            accepted_ids: List of accepted patch IDs
            rejected_ids: List of rejected patch IDs
        """
        try:
            # Get most recent turn
            response = (
                self.db.table("calendar_conversation_turns")
                .select("id")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"[CONVERSATION_MANAGER] No turns found for conversation {conversation_id}")
                return

            turn_id = response.data[0]["id"]

            # Update with patch actions
            update_data = {}
            if accepted_ids:
                update_data["accepted_patch_ids"] = accepted_ids
            if rejected_ids:
                update_data["rejected_patch_ids"] = rejected_ids

            if update_data:
                self.db.table("calendar_conversation_turns").update(update_data).eq("id", turn_id).execute()
                logger.info(f"[CONVERSATION_MANAGER] Recorded patch actions for turn {turn_id}")

        except Exception as e:
            logger.error(f"[CONVERSATION_MANAGER] Failed to record patch action: {e}", exc_info=True)
