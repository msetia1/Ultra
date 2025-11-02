"""WHOOP webhook processing."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import logging

from app.clients.whoop import WhoopApiClient
from app.services.whoop.ingestion import WhoopIngestionService
from app.services.whoop.sync_state import WhoopSyncStateRepository

logger = logging.getLogger(__name__)


class WhoopWebhookProcessor:
    """Translate WHOOP webhook payloads into ingestion tasks."""

    def __init__(self, ingestion: WhoopIngestionService, sync_state_repo: WhoopSyncStateRepository, api_client_factory) -> None:
        self.ingestion = ingestion
        self.sync_state_repo = sync_state_repo
        self.api_client_factory = api_client_factory

    async def handle_event(self, payload: Dict[str, Any], *, access_token: str, user_id: str) -> None:
        resource_type = payload.get("event_type") or payload.get("type")
        data = payload.get("resource") or payload.get("data") or payload
        async with self.api_client_factory(access_token) as client:
            if "sleep" in str(resource_type).lower() or data.get("sleep_id"):
                await self._handle_sleep_event(client, user_id, data)
            elif "workout" in str(resource_type).lower() or data.get("workout_id"):
                await self._handle_workout_event(client, user_id, data)
            elif "cycle" in str(resource_type).lower() or data.get("cycle_id"):
                await self._handle_cycle_event(client, user_id, data)
            elif "recovery" in str(resource_type).lower():
                await self._handle_recovery_event(client, user_id, data)
            else:
                logger.info("WHOOP webhook ignored", extra={"resource_type": resource_type})

    async def _handle_sleep_event(self, client: WhoopApiClient, user_id: str, data: Dict[str, Any]) -> None:
        sleep_id = data.get("sleep_id") or data.get("id")
        if sleep_id:
            record = await client.get_sleep(sleep_id)
            await self.ingestion.upsert_sleeps([self._map_sleep(user_id, record)])
        else:
            logger.debug("WHOOP sleep event without id", extra={"data": data})

    async def _handle_workout_event(self, client: WhoopApiClient, user_id: str, data: Dict[str, Any]) -> None:
        workout_id = data.get("workout_id") or data.get("id")
        if workout_id:
            record = await client.get_workout(workout_id)
            await self.ingestion.upsert_workouts([self._map_workout(user_id, record)])
        else:
            logger.debug("WHOOP workout event without id", extra={"data": data})

    async def _handle_cycle_event(self, client: WhoopApiClient, user_id: str, data: Dict[str, Any]) -> None:
        cycle_id = data.get("cycle_id") or data.get("id")
        if cycle_id:
            record = await client.get_cycle(cycle_id)
            await self.ingestion.upsert_cycles([self._map_cycle(user_id, record)])
        else:
            logger.debug("WHOOP cycle event without id", extra={"data": data})

    async def _handle_recovery_event(self, client: WhoopApiClient, user_id: str, data: Dict[str, Any]) -> None:
        cycle_id = data.get("cycle_id")
        if cycle_id:
            record = await client.get_recovery(str(cycle_id))
            await self.ingestion.upsert_recoveries([self._map_recovery(user_id, record)])
        else:
            logger.debug("WHOOP recovery event without cycle_id", extra={"data": data})

    def _map_recovery(self, user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        score = record.get("score") or {}
        return {
            "user_id": user_id,
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
            "raw_data": record,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }

    def _map_sleep(self, user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        score = record.get("score") or {}
        stage_summary = score.get("stage_summary") or {}
        sleep_needed = score.get("sleep_needed") or {}
        return {
            "user_id": user_id,
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
            "raw_data": record,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }

    def _map_workout(self, user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        score = record.get("score") or {}
        zones = score.get("zone_durations") or {}
        return {
            "user_id": user_id,
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
            "raw_data": record,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }

    def _map_cycle(self, user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        score = record.get("score") or {}
        return {
            "user_id": user_id,
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
            "raw_data": record,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }
