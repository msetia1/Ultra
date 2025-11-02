"""WHOOP service wiring and helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncContextManager, Callable, Optional
import logging

from app.database import get_supabase_client, SupabaseClient
from app.clients.whoop import whoop_client, WhoopOAuthClient, WhoopTokenRefresher, WhoopTokenBundle
from app.services.whoop.ingestion import WhoopIngestionService
from app.services.whoop.sync_state import WhoopSyncStateRepository
from app.services.whoop.backfill import WhoopBackfillCoordinator
from app.services.whoop.webhook import WhoopWebhookProcessor
from app.config import settings
from app.context_pipeline.sources.whoop import build_whoop_snapshot
from app.context_pipeline.services.payload_storage import PayloadStorageService
from app.context_pipeline.services.producer import record_context_event

logger = logging.getLogger(__name__)

__all__ = [
    "WhoopIngestionService",
    "WhoopBackfillCoordinator",
    "WhoopWebhookProcessor",
    "WhoopSyncStateRepository",
    "build_whoop_ingestion",
    "build_whoop_sync_repo",
    "build_whoop_coordinator",
    "build_whoop_webhook_processor",
    "get_whoop_oauth_client",
    "ensure_whoop_access_token",
]


def build_whoop_ingestion(db: Optional[SupabaseClient] = None) -> WhoopIngestionService:
    db = db or get_supabase_client()
    return WhoopIngestionService(db)


def build_whoop_sync_repo(db: Optional[SupabaseClient] = None) -> WhoopSyncStateRepository:
    db = db or get_supabase_client()
    return WhoopSyncStateRepository(db)


def _whoop_client_factory(access_token: str) -> AsyncContextManager:
    return whoop_client(access_token, timeout=settings.WHOOP_TIMEOUT_SECONDS)


def build_whoop_coordinator(db: Optional[SupabaseClient] = None) -> WhoopBackfillCoordinator:
    db = db or get_supabase_client()
    ingestion = build_whoop_ingestion(db)
    sync_repo = build_whoop_sync_repo(db)
    token_refresher = WhoopTokenRefresher(timeout=settings.WHOOP_TIMEOUT_SECONDS)
    return WhoopBackfillCoordinator(
        token_refresher=token_refresher,
        api_client_factory=_whoop_client_factory,
        ingestion=ingestion,
        sync_state_repo=sync_repo,
        default_days=settings.WHOOP_BACKFILL_DAYS,
    )


def build_whoop_webhook_processor(db: Optional[SupabaseClient] = None) -> WhoopWebhookProcessor:
    db = db or get_supabase_client()
    ingestion = build_whoop_ingestion(db)
    sync_repo = build_whoop_sync_repo(db)
    return WhoopWebhookProcessor(ingestion, sync_repo, _whoop_client_factory)


def get_whoop_oauth_client() -> WhoopOAuthClient:
    return WhoopOAuthClient(timeout=settings.WHOOP_TIMEOUT_SECONDS)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _should_refresh(expires_at: Optional[str]) -> bool:
    dt = _parse_timestamp(expires_at)
    if not dt:
        return True
    return dt <= datetime.now(timezone.utc) + timedelta(minutes=5)


async def ensure_whoop_access_token(
    user_id: str,
    *,
    db: Optional[SupabaseClient] = None,
    refresher: Optional[WhoopTokenRefresher] = None,
) -> WhoopTokenBundle:
    db = db or get_supabase_client()
    refresher = refresher or WhoopTokenRefresher(timeout=settings.WHOOP_TIMEOUT_SECONDS)
    client = db.admin_client or db.client
    resp = client.from_("whoop_auth").select("*").eq("user_id", user_id).limit(1).execute()
    rows = resp.data or []
    if not rows:
        raise RuntimeError("WHOOP not connected for user")
    row = rows[0]
    status = row.get("status")
    if status not in ("active", "pending"):
        raise RuntimeError("WHOOP integration inactive for user")
    access_token = row.get("access_token")
    refresh_token = row.get("refresh_token")
    expires_at = row.get("token_expires_at")
    bundle = WhoopTokenBundle(
        access_token=access_token or "",
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=None,
        expires_at=expires_at,
        scope=row.get("scopes"),
    )
    needs_refresh = not access_token or _should_refresh(expires_at)
    if not needs_refresh:
        return bundle
    if not refresh_token:
        raise RuntimeError("WHOOP refresh token missing")
    refreshed = await refresher.refresh(refresh_token)
    new_expires_at = refreshed.expires_at
    if not new_expires_at and refreshed.expires_in:
        new_expires_at_dt = datetime.now(timezone.utc) + timedelta(seconds=refreshed.expires_in)
        new_expires_at = new_expires_at_dt.isoformat()
    update_payload = {
        "access_token": refreshed.access_token,
        "token_expires_at": new_expires_at,
        "last_refreshed_at": datetime.utcnow().isoformat() + "Z",
        "status": "active",
    }
    if refreshed.refresh_token:
        update_payload["refresh_token"] = refreshed.refresh_token
    if refreshed.scope:
        update_payload["scopes"] = refreshed.scope
    client.from_("whoop_auth").update(update_payload).eq("user_id", user_id).execute()
    return WhoopTokenBundle(
        access_token=refreshed.access_token,
        refresh_token=refreshed.refresh_token or refresh_token,
        token_type=refreshed.token_type,
        expires_in=refreshed.expires_in,
        expires_at=new_expires_at,
        scope=refreshed.scope,
    )


async def publish_whoop_context_update(user_id: str) -> None:
    """Compute latest WHOOP snapshot and enqueue a context-window update."""
    snapshot = await build_whoop_snapshot(user_id)
    storage = PayloadStorageService()
    payload_id = await storage.store_payload(snapshot, user_id=user_id, event_type="whoop_update")
    record_context_event(user_id, None, "whoop_update", payload_id, "whoop_backend")
