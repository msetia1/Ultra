
"""WHOOP OAuth endpoints."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import AuthUser, get_current_user
from app.config import settings
from app.database import SupabaseClient, get_supabase_client
from app.services.whoop import get_whoop_oauth_client
from app.clients.whoop import whoop_client
from app.tasks.whoop import kickoff_initial_backfill

logger = logging.getLogger(__name__)

router = APIRouter()

_STATE_STORE: Dict[str, Dict[str, Optional[str]]] = {}
_STATE_TTL_SECONDS = 15 * 60
_SCOPES = "offline read:recovery read:cycles read:workout read:sleep read:profile read:body_measurement"


def _cleanup_state() -> None:
    cutoff = time.time() - _STATE_TTL_SECONDS
    for key, val in list(_STATE_STORE.items()):
        created_at = val.get("created_at")
        if created_at is None or float(created_at) < cutoff or val.get("used_at"):
            _STATE_STORE.pop(key, None)


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(48)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _resolve_redirect_uri(request: Request) -> str:
    if settings.WHOOP_REDIRECT_URI:
        return settings.WHOOP_REDIRECT_URI
    return str(request.url_for("whoop_callback"))


def _frontend_redirect_url(request: Request) -> str:
    env_frontend = os.getenv("FRONTEND_URL")
    if env_frontend:
        return env_frontend.rstrip('/') + '/account'
    return request.headers.get("referer") or "/"


@router.get("/authorize")
async def authorize_whoop(request: Request, current_user: AuthUser = Depends(get_current_user)):
    """Initiate WHOOP OAuth by returning an authorize URL."""
    if not settings.WHOOP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="WHOOP client credentials not configured")
    _cleanup_state()
    verifier, challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(24)
    # Use explicit redirect_uri from query params if provided (e.g., for iOS), otherwise auto-generate
    redirect_uri = request.query_params.get("redirect_uri") or _resolve_redirect_uri(request)
    _STATE_STORE[state] = {
        "user_id": str(current_user.user_id),
        "code_verifier": verifier,
        "created_at": str(time.time()),
        "redirect_uri": redirect_uri,
        "used_at": None,
    }
    params = {
        "response_type": "code",
        "client_id": settings.WHOOP_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": _SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{settings.WHOOP_AUTH_URL}?{urlencode(params)}"
    logger.info("WHOOP authorize redirect", extra={"user_id": str(current_user.user_id), "redirect_uri": redirect_uri, "authorize_url": authorize_url})
    wants_json = request.query_params.get("mode") == "json" or "application/json" in (request.headers.get("accept", "").lower())
    if wants_json:
        return JSONResponse({"authorize_url": authorize_url})
    return RedirectResponse(url=authorize_url)


@router.get("/callback", name="whoop_callback")
async def whoop_callback(request: Request, db: SupabaseClient = Depends(get_supabase_client)):
    """Handle WHOOP OAuth callback."""
    # Disable LangSmith tracing for this endpoint to prevent memory issues
    try:
        from app.instrumentation.langsmith import set_tracing_disabled
        set_tracing_disabled(True)
    except Exception:
        pass  # If tracing module doesn't exist, continue anyway

    start_time = time.time()
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    logger.info("[WHOOP_CB] START - code=%s state=%s", bool(code), bool(state))
    sys.stdout.flush()

    if error:
        logger.error("[WHOOP_CB] OAuth error: %s", error)
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail=f"WHOOP authorization failed: {error}")
    if not code or not state:
        logger.error("[WHOOP_CB] Missing code or state")
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail="Missing code or state")
    rec = _STATE_STORE.get(state)
    if not rec:
        logger.error("[WHOOP_CB] Invalid or expired state")
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    if rec.get("used_at"):
        logger.error("[WHOOP_CB] State already used")
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail="State already used")
    created_at = float(rec.get("created_at") or 0)
    if created_at < time.time() - _STATE_TTL_SECONDS:
        _STATE_STORE.pop(state, None)
        logger.error("[WHOOP_CB] State expired")
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail="State expired")

    user_id = rec["user_id"]
    logger.info("WHOOP callback started", extra={"user_id": user_id, "elapsed_ms": 0})
    sys.stdout.flush()

    # Token exchange with timeout protection
    token_start = time.time()
    logger.info("WHOOP token exchange starting", extra={"user_id": user_id, "elapsed_ms": int((token_start - start_time) * 1000)})
    sys.stdout.flush()

    try:
        oauth_client = get_whoop_oauth_client()
        async with oauth_client:
            token_bundle = await asyncio.wait_for(
                oauth_client.exchange_code(
                    code,
                    redirect_uri=rec["redirect_uri"],
                    code_verifier=rec.get("code_verifier"),
                    scope=_SCOPES,
                ),
                timeout=15.0
            )
    except asyncio.TimeoutError:
        logger.error("[WHOOP_CB] Token exchange timeout", extra={"user_id": user_id})
        sys.stdout.flush()
        raise HTTPException(status_code=504, detail="WHOOP token exchange timeout")

    token_duration = int((time.time() - token_start) * 1000)
    logger.info("WHOOP token exchange completed", extra={"user_id": user_id, "duration_ms": token_duration, "elapsed_ms": int((time.time() - start_time) * 1000)})
    sys.stdout.flush()

    # Profile fetch with timeout protection
    profile_start = time.time()
    logger.info("WHOOP profile fetch starting", extra={"user_id": user_id, "elapsed_ms": int((profile_start - start_time) * 1000)})
    sys.stdout.flush()

    try:
        async with whoop_client(token_bundle.access_token) as client:
            profile = await asyncio.wait_for(
                client.get_user_profile(),
                timeout=10.0
            )
    except asyncio.TimeoutError:
        logger.error("[WHOOP_CB] Profile fetch timeout", extra={"user_id": user_id})
        sys.stdout.flush()
        raise HTTPException(status_code=504, detail="WHOOP profile fetch timeout")

    profile_duration = int((time.time() - profile_start) * 1000)
    logger.info("WHOOP profile fetch completed", extra={"user_id": user_id, "duration_ms": profile_duration, "elapsed_ms": int((time.time() - start_time) * 1000)})
    sys.stdout.flush()

    whoop_user_id = profile.get("user_id")
    if whoop_user_id is None:
        logger.error("[WHOOP_CB] Unable to resolve WHOOP user id", extra={"user_id": user_id})
        sys.stdout.flush()
        raise HTTPException(status_code=400, detail="Unable to resolve WHOOP user id")
    whoop_user_id = str(whoop_user_id)
    expires_at = token_bundle.expires_at
    if not expires_at and token_bundle.expires_in:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_bundle.expires_in)).isoformat()
    payload = {
        "user_id": rec["user_id"],
        "whoop_user_id": whoop_user_id,
        "access_token": token_bundle.access_token,
        "refresh_token": token_bundle.refresh_token,
        "token_expires_at": expires_at,
        "scopes": token_bundle.scope or _SCOPES,
        "connected_at": datetime.utcnow().isoformat() + "Z",
        "status": "active",
        "last_refreshed_at": datetime.utcnow().isoformat() + "Z",
    }

    # DB upsert
    db_start = time.time()
    logger.info("WHOOP DB upsert starting", extra={"user_id": user_id, "elapsed_ms": int((db_start - start_time) * 1000)})
    sys.stdout.flush()
    table = db.admin_client or db.client
    table.from_("whoop_auth").upsert(payload, on_conflict="user_id").execute()
    db_duration = int((time.time() - db_start) * 1000)
    logger.info("WHOOP DB upsert completed", extra={"user_id": user_id, "duration_ms": db_duration, "elapsed_ms": int((time.time() - start_time) * 1000)})
    sys.stdout.flush()

    _STATE_STORE[state]["used_at"] = str(time.time())

    # Celery enqueue
    celery_start = time.time()
    logger.info("WHOOP backfill enqueue starting", extra={"user_id": user_id, "elapsed_ms": int((celery_start - start_time) * 1000)})
    sys.stdout.flush()
    kickoff_initial_backfill.delay(user_id=str(rec["user_id"]))
    celery_duration = int((time.time() - celery_start) * 1000)
    logger.info("WHOOP backfill enqueue completed", extra={"user_id": user_id, "duration_ms": celery_duration, "elapsed_ms": int((time.time() - start_time) * 1000)})
    sys.stdout.flush()

    total_duration = int((time.time() - start_time) * 1000)
    logger.info("WHOOP callback completed", extra={"user_id": user_id, "total_duration_ms": total_duration})
    sys.stdout.flush()

    redirect_target = _frontend_redirect_url(request)
    sep = '&' if '?' in redirect_target else '?'
    redirect_target = f"{redirect_target}{sep}whoop_connected=true"
    return RedirectResponse(url=redirect_target)


@router.delete("/disconnect")
async def disconnect_whoop(current_user: AuthUser = Depends(get_current_user), db: SupabaseClient = Depends(get_supabase_client)):
    """Disconnect WHOOP integration for the current user."""
    table = db.admin_client or db.client
    result = table.from_("whoop_auth").update({
        "status": "disconnected",
        "access_token": None,
        "refresh_token": None,
        "token_expires_at": None,
    }).eq("user_id", current_user.user_id).execute()

    logger.info("WHOOP disconnected", extra={"user_id": str(current_user.user_id)})

    return {"success": True, "message": "Successfully disconnected from WHOOP"}
