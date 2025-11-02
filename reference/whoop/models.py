"""Pydantic models reflecting WHOOP API payloads.

These models allow downstream services to work with typed objects rather than
raw dictionaries while still permitting forward-compatible fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class _Config:
    extra = "allow"


class RecoveryScore(BaseModel):
    user_calibrating: bool
    recovery_score: Optional[float] = None
    resting_heart_rate: Optional[float] = None
    hrv_rmssd_milli: Optional[float] = None
    spo2_percentage: Optional[float] = None
    skin_temp_celsius: Optional[float] = None

    class Config(_Config):
        pass


class RecoveryRecord(BaseModel):
    cycle_id: int
    sleep_id: Optional[str] = None
    user_id: int
    created_at: datetime
    updated_at: datetime
    score_state: str
    score: Optional[RecoveryScore] = None

    class Config(_Config):
        pass


class SleepStageSummary(BaseModel):
    total_in_bed_time_milli: Optional[int] = None
    total_awake_time_milli: Optional[int] = None
    total_no_data_time_milli: Optional[int] = None
    total_light_sleep_time_milli: Optional[int] = None
    total_slow_wave_sleep_time_milli: Optional[int] = None
    total_rem_sleep_time_milli: Optional[int] = None
    sleep_cycle_count: Optional[int] = None
    disturbance_count: Optional[int] = None

    class Config(_Config):
        pass


class SleepNeeded(BaseModel):
    baseline_milli: Optional[int] = None
    need_from_sleep_debt_milli: Optional[int] = None
    need_from_recent_strain_milli: Optional[int] = None
    need_from_recent_nap_milli: Optional[int] = None

    class Config(_Config):
        pass


class SleepScore(BaseModel):
    stage_summary: Optional[SleepStageSummary] = None
    sleep_needed: Optional[SleepNeeded] = None
    respiratory_rate: Optional[float] = None
    sleep_performance_percentage: Optional[float] = None
    sleep_consistency_percentage: Optional[float] = None
    sleep_efficiency_percentage: Optional[float] = None

    class Config(_Config):
        pass


class SleepRecord(BaseModel):
    id: str
    cycle_id: Optional[int] = None
    v1_id: Optional[int] = None
    user_id: int
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: datetime
    timezone_offset: Optional[str] = None
    nap: bool
    score_state: str
    score: Optional[SleepScore] = None

    class Config(_Config):
        pass


class ZoneDurations(BaseModel):
    zone_zero_milli: Optional[int] = None
    zone_one_milli: Optional[int] = None
    zone_two_milli: Optional[int] = None
    zone_three_milli: Optional[int] = None
    zone_four_milli: Optional[int] = None
    zone_five_milli: Optional[int] = None

    class Config(_Config):
        pass


class WorkoutScore(BaseModel):
    strain: Optional[float] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    kilojoule: Optional[float] = None
    percent_recorded: Optional[float] = None
    distance_meter: Optional[float] = None
    altitude_gain_meter: Optional[float] = None
    altitude_change_meter: Optional[float] = None
    zone_durations: Optional[ZoneDurations] = None

    class Config(_Config):
        pass


class WorkoutRecord(BaseModel):
    id: str
    v1_id: Optional[int] = None
    user_id: int
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: datetime
    timezone_offset: Optional[str] = None
    sport_name: Optional[str] = None
    sport_id: Optional[int] = None
    score_state: str
    score: Optional[WorkoutScore] = None

    class Config(_Config):
        pass


class CycleScore(BaseModel):
    strain: Optional[float] = None
    kilojoule: Optional[float] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None

    class Config(_Config):
        pass


class CycleRecord(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    start: datetime
    end: Optional[datetime] = None
    timezone_offset: Optional[str] = None
    score_state: str
    score: Optional[CycleScore] = None

    class Config(_Config):
        pass
