"""WHOOP ingestion service."""
from __future__ import annotations

from typing import Iterable, Mapping, Any
from collections import OrderedDict
import logging

from app.database import SupabaseClient

logger = logging.getLogger(__name__)


WHOOP_RECOVERY_TABLE = "whoop_recovery"
WHOOP_SLEEP_TABLE = "whoop_sleep"
WHOOP_WORKOUT_TABLE = "whoop_workouts"
WHOOP_CYCLE_TABLE = "whoop_cycles"


class WhoopIngestionService:
    """Persist WHOOP resources into Supabase tables."""

    def __init__(self, db: SupabaseClient) -> None:
        self.db = db

    async def upsert_recoveries(self, rows: Iterable[Mapping[str, Any]]) -> None:
        deduped = self._deduplicate_on_key(rows, "whoop_cycle_id")
        await self._batch_upsert(WHOOP_RECOVERY_TABLE, deduped, on_conflict="whoop_cycle_id")

    async def upsert_sleeps(self, rows: Iterable[Mapping[str, Any]]) -> None:
        await self._batch_upsert(WHOOP_SLEEP_TABLE, rows, on_conflict="whoop_sleep_id")

    async def upsert_workouts(self, rows: Iterable[Mapping[str, Any]]) -> None:
        await self._batch_upsert(WHOOP_WORKOUT_TABLE, rows, on_conflict="whoop_workout_id")

    async def upsert_cycles(self, rows: Iterable[Mapping[str, Any]]) -> None:
        await self._batch_upsert(WHOOP_CYCLE_TABLE, rows, on_conflict="whoop_cycle_id")

    def _deduplicate_on_key(self, rows: Iterable[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
        """Return rows with the latest occurrence per key; WHOOP can emit duplicates within a page."""
        rows_list = [dict(row) for row in rows if row]
        if key is None:
            return rows_list
        
        # Group by key, keeping the last occurrence of each key
        seen: dict[Any, Mapping[str, Any]] = {}
        for row_dict in rows_list:
            value = row_dict.get(key)
            if value is None:
                # For None keys, use a unique identifier to avoid overwriting
                unique_key = f"_none_{id(row_dict)}"
                seen[unique_key] = row_dict
            else:
                # Convert to string to ensure consistent key types
                normalized_key = str(value) if value is not None else None
                seen[normalized_key] = row_dict
        
        deduped = list(seen.values())
        if len(rows_list) != len(deduped):
            duplicates_removed = len(rows_list) - len(deduped)
            logger.info("WHOOP dedupe removed duplicates", extra={
                "key": key, 
                "incoming": len(rows_list), 
                "deduped": len(deduped),
                "duplicates_removed": duplicates_removed
            })
        return deduped

    async def _batch_upsert(self, table: str, rows: Iterable[Mapping[str, Any]], *, on_conflict: str) -> None:
        payload = [dict(row) for row in rows if row]
        if not payload:
            logger.debug("WHOOP ingestion skipping empty batch", extra={"table": table})
            return
        client = self.db.admin_client or self.db.client
        logger.debug("WHOOP ingestion upserting", extra={"table": table, "count": len(payload)})
        client.from_(table).upsert(payload, on_conflict=on_conflict).execute()
