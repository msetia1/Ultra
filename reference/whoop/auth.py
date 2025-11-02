"""WHOOP OAuth helpers.

Provides token exchange and refresh utilities compatible with the official
WHOOP OAuth2 endpoints documented in docs/WHOOP_API.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WhoopTokenBundle:
    """Container for WHOOP OAuth tokens and metadata."""

    access_token: str
    refresh_token: Optional[str]
    token_type: Optional[str]
    expires_in: Optional[int]
    expires_at: Optional[str]
    scope: Optional[str]


class WhoopOAuthClient:
    """Lightweight async client for WHOOP OAuth token workflows."""

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._client_id = client_id or settings.WHOOP_CLIENT_ID
        self._client_secret = client_secret or settings.WHOOP_CLIENT_SECRET
        self._timeout = timeout or settings.WHOOP_TIMEOUT_SECONDS
        self._client = http_client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "WhoopOAuthClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def exchange_code(
        self,
        code: str,
        *,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> WhoopTokenBundle:
        """Exchange an authorization code for tokens."""
        form = {
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            form["code_verifier"] = code_verifier
        if scope:
            form["scope"] = scope
        return await self._post_token(form)

    async def refresh(self, refresh_token: str) -> WhoopTokenBundle:
        """Refresh an access token using the provided refresh token."""
        form = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
        }
        bundle = await self._post_token(form)
        # WHOOP may or may not return a new refresh token; preserve the old one.
        if not bundle.refresh_token:
            bundle.refresh_token = refresh_token
        return bundle

    async def _post_token(self, form: dict) -> WhoopTokenBundle:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = await self._client.post(settings.WHOOP_TOKEN_URL, data=form, headers=headers)
        response.raise_for_status()
        payload = response.json()
        logger.debug("WHOOP token response received", extra={"keys": list(payload.keys())})
        return WhoopTokenBundle(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            token_type=payload.get("token_type"),
            expires_in=payload.get("expires_in"),
            expires_at=payload.get("expires_at"),
            scope=payload.get("scope"),
        )


class WhoopTokenRefresher:
    """Convenience wrapper that refreshes tokens using WhoopOAuthClient."""

    def __init__(self, *, timeout: Optional[float] = None) -> None:
        self._timeout = timeout or settings.WHOOP_TIMEOUT_SECONDS

    async def refresh(self, refresh_token: str) -> WhoopTokenBundle:
        async with WhoopOAuthClient(timeout=self._timeout) as client:
            return await client.refresh(refresh_token)
