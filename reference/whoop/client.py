"""WHOOP API client built on top of HTTPX.

This client centralizes authenticated requests, pagination helpers, and
resource-specific fetch utilities aligned with docs/WHOOP_API.md.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WhoopApiClient:
    """Async client for the WHOOP Developer API."""

    def __init__(
        self,
        access_token: str,
        *,
        timeout: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._access_token = access_token
        self._timeout = timeout or settings.WHOOP_TIMEOUT_SECONDS
        self._base_url = settings.WHOOP_API_BASE_URL.rstrip('/')
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "WhoopApiClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform a GET request and return parsed JSON."""
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def list_paginated(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        page_size: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield WHOOP records page by page."""
        query = dict(params or {})
        if page_size and "limit" not in query:
            query["limit"] = page_size
        elif "limit" not in query:
            query["limit"] = settings.WHOOP_DEFAULT_PAGE_SIZE

        next_token: Optional[str] = query.get("nextToken")
        while True:
            if next_token:
                query["nextToken"] = next_token
            data = await self.get_json(path, params=query)
            records = data.get("records", [])
            logger.debug(
                "WHOOP paginated fetch",
                extra={"path": path, "count": len(records), "has_next": bool(data.get("next_token"))},
            )
            for record in records:
                yield record
            next_token = data.get("next_token")
            if not next_token:
                break

    async def list_recoveries(self, **params: Any) -> AsyncIterator[Dict[str, Any]]:
        """Iterate recoveries using WHOOP pagination."""
        async for record in self.list_paginated("/v2/recovery", params=params):
            yield record

    async def list_sleep(self, **params: Any) -> AsyncIterator[Dict[str, Any]]:
        """Iterate sleep records using WHOOP pagination."""
        async for record in self.list_paginated("/v2/activity/sleep", params=params):
            yield record

    async def list_workouts(self, **params: Any) -> AsyncIterator[Dict[str, Any]]:
        """Iterate workout records using WHOOP pagination."""
        async for record in self.list_paginated("/v2/activity/workout", params=params):
            yield record

    async def list_cycles(self, **params: Any) -> AsyncIterator[Dict[str, Any]]:
        """Iterate physiological cycles using WHOOP pagination."""
        async for record in self.list_paginated("/v2/cycle", params=params):
            yield record

    async def get_cycle(self, cycle_id: int) -> Dict[str, Any]:
        return await self.get_json(f"/v2/cycle/{cycle_id}")

    async def get_cycle_sleep(self, cycle_id: int) -> Dict[str, Any]:
        return await self.get_json(f"/v2/cycle/{cycle_id}/sleep")

    async def get_workout(self, workout_id: str) -> Dict[str, Any]:
        return await self.get_json(f"/v2/activity/workout/{workout_id}")

    async def get_sleep(self, sleep_id: str) -> Dict[str, Any]:
        return await self.get_json(f"/v2/activity/sleep/{sleep_id}")

    async def get_recovery(self, recovery_id: str) -> Dict[str, Any]:
        return await self.get_json(f"/v2/recovery/{recovery_id}")

    async def get_user_profile(self) -> Dict[str, Any]:
        return await self.get_json("/v2/user/profile/basic")


@asynccontextmanager
async def whoop_client(access_token: str, *, timeout: Optional[float] = None) -> AsyncIterator[WhoopApiClient]:
    client = WhoopApiClient(access_token, timeout=timeout)
    try:
        yield client
    finally:
        await client.close()
