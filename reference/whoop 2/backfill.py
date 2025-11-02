"""WHOOP backfill coordination."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, Optional
import logging

from app.clients.whoop import WhoopApiClient
from app.clients.whoop.auth import WhoopTokenRefresher
from app.services.whoop.ingestion import WhoopIngestionService
from app.services.whoop.sync_state import WhoopSyncStateRepository, WhoopSyncState

logger = logging.getLogger(__name__)

DEFAULT_RESOURCES = {
    "recovery": {
        "list_method": "list_recoveries",
        "upsert": "upsert_recoveries",
        "id_field": "whoop_cycle_id",
    },
    "sleep": {
        "list_method": "list_sleep",
        "upsert": "upsert_sleeps",
        "id_field": "whoop_sleep_id",
    },
    "workout": {
        "list_method": "list_workouts",
        "upsert": "upsert_workouts",
        "id_field": "whoop_workout_id",
    },
    "cycle": {
        "list_method": "list_cycles",
        "upsert": "upsert_cycles",
        "id_field": "whoop_cycle_id",
    },
}


class WhoopBackfillCoordinator:
    """Coordinates historical backfill windows and incremental syncs."""

    def __init__(
        self,
        token_refresher: WhoopTokenRefresher,
        api_client_factory: Callable[[str], WhoopApiClient],
        ingestion: WhoopIngestionService,
        sync_state_repo: WhoopSyncStateRepository,
        *,
        default_days: int = 180,
    ) -> None:
        self.token_refresher = token_refresher
        self.api_client_factory = api_client_factory
        self.ingestion = ingestion
        self.sync_state_repo = sync_state_repo
        self.default_days = default_days

    async def run_initial_backfill(self, user_id: str, access_token: str, *, days: Optional[int] = None) -> None:
        window_days = days or self.default_days
        start_utc = datetime.now(timezone.utc) - timedelta(days=window_days)
        await self._sync_resources(user_id, access_token, since=start_utc.isoformat(), label="initial")

    async def run_incremental_sync(self, user_id: str, access_token: str) -> None:
        await self._sync_resources(user_id, access_token, since=None, label="incremental")

    async def _sync_resources(self, user_id: str, access_token: str, *, since: Optional[str], label: str) -> None:
        async with self.api_client_factory(access_token) as client:
            for resource, cfg in DEFAULT_RESOURCES.items():
                try:
                    await self._sync_single_resource(user_id, resource, client, cfg, since=since)
                    await self.sync_state_repo.clear_error(user_id, resource)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.exception("WHOOP %s sync failed", resource, extra={"user_id": user_id, "label": label})
                    await self.sync_state_repo.mark_error(user_id, resource, error_code="sync_failed", error_message=str(exc))

    async def _sync_single_resource(
        self,
        user_id: str,
        resource: str,
        client: WhoopApiClient,
        cfg: Dict[str, str],
        *,
        since: Optional[str],
    ) -> None:
        state = await self.sync_state_repo.get_state(user_id, resource)
        params: Dict[str, str] = {}
        if since:
            params["start"] = since
        elif state and state.last_end:
            params["start"] = state.last_end
        list_method = getattr(client, cfg["list_method"])
        records = []
        async for record in list_method(**params):  # type: ignore[func-returns-value]
            records.append(record)
        if not records:
            logger.debug("WHOOP sync no records", extra={"user_id": user_id, "resource": resource})
            return
        await self._persist_records(user_id, resource, records, cfg)
        last_record = records[0]
        end_ts = last_record.get("created_at") or last_record.get("end") or last_record.get("updated_at")
        new_state = WhoopSyncState(
            user_id=user_id,
            resource=resource,
            last_start=params.get("start"),
            last_end=end_ts,
            next_token=None,
            status="synced",
        )
        await self.sync_state_repo.upsert_state(new_state)

    async def _persist_records(self, user_id: str, resource: str, records: Iterable[Dict], cfg: Dict[str, str]) -> None:
        upsert_method = getattr(self.ingestion, cfg["upsert"])
        
        # Convert iterator to list to avoid consumption issues
        records_list = list(records)
        
        transformed = []
        for record in records_list:
            mapped = self._map_record(user_id, resource, record, cfg)
            transformed.append(mapped)
            
        # Additional deduplication at mapped level for recovery to prevent Supabase conflicts
        if resource == "recovery":
            mapped_cycle_ids = [row.get("whoop_cycle_id") for row in transformed]
            unique_cycle_ids = len(set(mapped_cycle_ids))
            if len(transformed) != unique_cycle_ids:
                logger.warning("WHOOP duplicate cycle_ids detected in mapped data", extra={
                    "user_id": user_id,
                    "total_records": len(transformed),
                    "unique_cycle_ids": unique_cycle_ids,
                    "duplicates": len(transformed) - unique_cycle_ids
                })
                
                # Deduplicate by keeping the last occurrence of each cycle_id
                dedupe_dict = {}
                for row in transformed:
                    cycle_id = row.get("whoop_cycle_id")
                    if cycle_id:
                        dedupe_dict[str(cycle_id)] = row  # Normalize to string and keep last occurrence
                    else:
                        # Handle None cycle_ids by giving them unique keys
                        unique_key = f"none_{id(row)}"
                        dedupe_dict[unique_key] = row
                        
                transformed = list(dedupe_dict.values())
                logger.info("WHOOP coordinator dedupe completed", extra={
                    "user_id": user_id,
                    "original_count": len(mapped_cycle_ids),
                    "final_count": len(transformed),
                    "removed_duplicates": len(mapped_cycle_ids) - len(transformed)
                })
            
        await upsert_method(transformed)

    def _map_record(self, user_id: str, resource: str, record: Dict, cfg: Dict[str, str]) -> Dict:
        base = {
            "user_id": user_id,
            "raw_data": record,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }
        mapper_name = f"_map_{resource}"
        mapper = getattr(self, mapper_name)
        mapped = mapper(record)
        base.update(mapped)
        return base

    def _map_recovery(self, record: Dict) -> Dict:
        score = record.get("score") or {}
        return {
            "whoop_cycle_id": str(record.get("cycle_id")),
            "whoop_sleep_id": record.get("sleep_id"),
            "whoop_user_id": record.get("user_id"),
            "whoop_created_at": record.get("created_at"),
            "whoop_updated_at": record.get("updated_at"),
            "score_state": record.get("score_state"),
            "user_calibrating": score.get("user_calibrating"),
            "recovery_score": score.get("recovery_score"),
            "resting_heart_rate": score.get("resting_heart_rate"),
            "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
            "spo2_percentage": score.get("spo2_percentage"),
            "skin_temp_celsius": score.get("skin_temp_celsius"),
        }

    def _map_sleep(self, record: Dict) -> Dict:
        score = record.get("score") or {}
        stage_summary = score.get("stage_summary") or {}
        sleep_needed = score.get("sleep_needed") or {}
        return {
            "whoop_sleep_id": record.get("id"),
            "whoop_cycle_id": str(record.get("cycle_id")) if record.get("cycle_id") else None,
            "whoop_user_id": record.get("user_id"),
            "whoop_created_at": record.get("created_at"),
            "whoop_updated_at": record.get("updated_at"),
            "whoop_v1_id": record.get("v1_id"),
            "sleep_start": record.get("start"),
            "sleep_end": record.get("end"),
            "timezone_offset": record.get("timezone_offset"),
            "nap": record.get("nap"),
            "score_state": record.get("score_state"),
            "sleep_performance_percentage": score.get("sleep_performance_percentage"),
            "sleep_consistency_percentage": score.get("sleep_consistency_percentage"),
            "sleep_efficiency_percentage": score.get("sleep_efficiency_percentage"),
            "respiratory_rate": score.get("respiratory_rate"),
            "total_in_bed_time_milli": stage_summary.get("total_in_bed_time_milli"),
            "total_awake_time_milli": stage_summary.get("total_awake_time_milli"),
            "total_no_data_time_milli": stage_summary.get("total_no_data_time_milli"),
            "total_light_sleep_time_milli": stage_summary.get("total_light_sleep_time_milli"),
            "total_slow_wave_sleep_time_milli": stage_summary.get("total_slow_wave_sleep_time_milli"),
            "total_rem_sleep_time_milli": stage_summary.get("total_rem_sleep_time_milli"),
            "sleep_cycle_count": stage_summary.get("sleep_cycle_count"),
            "disturbance_count": stage_summary.get("disturbance_count"),
            "sleep_need_baseline_milli": sleep_needed.get("baseline_milli"),
            "sleep_need_need_from_sleep_debt_milli": sleep_needed.get("need_from_sleep_debt_milli"),
            "sleep_need_need_from_recent_strain_milli": sleep_needed.get("need_from_recent_strain_milli"),
            "sleep_need_need_from_recent_nap_milli": sleep_needed.get("need_from_recent_nap_milli"),
        }

    def _map_workout(self, record: Dict) -> Dict:
        score = record.get("score") or {}
        zones = score.get("zone_durations") or {}
        return {
            "whoop_workout_id": record.get("id"),
            "whoop_user_id": record.get("user_id"),
            "whoop_created_at": record.get("created_at"),
            "whoop_updated_at": record.get("updated_at"),
            "whoop_v1_id": record.get("v1_id"),
            "workout_start": record.get("start"),
            "workout_end": record.get("end"),
            "timezone_offset": record.get("timezone_offset"),
            "score_state": record.get("score_state"),
            "sport_name": record.get("sport_name"),
            "sport_id": record.get("sport_id"),
            "strain": score.get("strain"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
            "kilojoule": score.get("kilojoule"),
            "percent_recorded": score.get("percent_recorded"),
            "distance_meter": score.get("distance_meter"),
            "altitude_gain_meter": score.get("altitude_gain_meter"),
            "altitude_change_meter": score.get("altitude_change_meter"),
            "zone_zero_milli": zones.get("zone_zero_milli"),
            "zone_one_milli": zones.get("zone_one_milli"),
            "zone_two_milli": zones.get("zone_two_milli"),
            "zone_three_milli": zones.get("zone_three_milli"),
            "zone_four_milli": zones.get("zone_four_milli"),
            "zone_five_milli": zones.get("zone_five_milli"),
        }

    def _map_cycle(self, record: Dict) -> Dict:
        score = record.get("score") or {}
        return {
            "whoop_cycle_id": str(record.get("id")),
            "whoop_user_id": record.get("user_id"),
            "whoop_created_at": record.get("created_at"),
            "whoop_updated_at": record.get("updated_at"),
            "cycle_start": record.get("start"),
            "cycle_end": record.get("end"),
            "timezone_offset": record.get("timezone_offset"),
            "score_state": record.get("score_state"),
            "strain": score.get("strain"),
            "kilojoule": score.get("kilojoule"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
        }
