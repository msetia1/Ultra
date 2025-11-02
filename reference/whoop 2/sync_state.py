"""Persistence helpers for WHOOP sync cursors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import logging

from app.database import SupabaseClient

logger = logging.getLogger(__name__)

WHOOP_SYNC_STATE_TABLE = "whoop_sync_state"


@dataclass
class WhoopSyncState:
    user_id: str
    resource: str
    last_start: Optional[str] = None
    last_end: Optional[str] = None
    next_token: Optional[str] = None
    status: str = "idle"
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_record(self) -> dict:
        payload = {
            "user_id": self.user_id,
            "resource_type": self.resource,
            "last_start": self.last_start,
            "last_end": self.last_end,
            "next_token": self.next_token,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        return payload


class WhoopSyncStateRepository:
    """Read/write WHOOP sync progress from Supabase."""

    def __init__(self, db: SupabaseClient) -> None:
        self.db = db

    async def get_state(self, user_id: str, resource: str) -> Optional[WhoopSyncState]:
        client = self.db.admin_client or self.db.client
        resp = client.from_(WHOOP_SYNC_STATE_TABLE).select("*", count="exact").eq("user_id", user_id).eq("resource_type", resource).limit(1).execute()
        data = resp.data or []
        if not data:
            return None
        row = data[0]
        return WhoopSyncState(
            user_id=row.get("user_id"),
            resource=row.get("resource_type"),
            last_start=row.get("last_start"),
            last_end=row.get("last_end"),
            next_token=row.get("next_token"),
            status=row.get("status", "idle"),
            error_code=row.get("error_code"),
            error_message=row.get("error_message"),
        )

    async def upsert_state(self, state: WhoopSyncState) -> None:
        client = self.db.admin_client or self.db.client
        payload = state.to_record()
        logger.debug("WHOOP sync state upsert", extra={"user_id": state.user_id, "resource": state.resource})
        client.from_(WHOOP_SYNC_STATE_TABLE).upsert(payload, on_conflict="user_id,resource_type").execute()

    async def mark_error(self, user_id: str, resource: str, *, error_code: Optional[str], error_message: Optional[str]) -> None:
        state = WhoopSyncState(user_id=user_id, resource=resource, status="error", error_code=error_code, error_message=error_message)
        await self.upsert_state(state)

    async def clear_error(self, user_id: str, resource: str) -> None:
        current = await self.get_state(user_id, resource)
        if not current:
            return
        current.status = "idle"
        current.error_code = None
        current.error_message = None
        await self.upsert_state(current)
