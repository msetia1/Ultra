"""WHOOP OAuth 2.0 integration service.

Implements the full OAuth flow per WHOOP documentation:
https://developer.whoop.com/docs/developing/oauth/
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
import requests
from dotenv import load_dotenv

from integrations.supabase_service import get_supabase

load_dotenv()

# WHOOP OAuth configuration from environment
WHOOP_CLIENT_ID = os.environ["WHOOP_CLIENT_ID"]
WHOOP_CLIENT_SECRET = os.environ["WHOOP_CLIENT_SECRET"]
WHOOP_API_HOSTNAME = os.environ["WHOOP_API_HOSTNAME"]
WHOOP_CALLBACK_URL = os.environ.get("WHOOP_CALLBACK_URL", "http://localhost:8000/auth/whoop/callback")

# WHOOP OAuth endpoints
WHOOP_AUTH_URL = f"{WHOOP_API_HOSTNAME}/oauth/oauth2/auth"
WHOOP_TOKEN_URL = f"{WHOOP_API_HOSTNAME}/oauth/oauth2/token"

# Scopes for accessing WHOOP data
DEFAULT_SCOPES = "offline read:recovery read:workout read:sleep read:cycles read:profile"


def build_authorization_url(user_id: str) -> Tuple[str, str]:
	"""Generate WHOOP OAuth authorization URL.
	
	Per WHOOP docs, state parameter must be 8 characters long for security.
	
	Args:
		user_id: The user's UUID from auth.users
		
	Returns:
		Tuple of (authorization_url, state_token)
	"""
	# Generate 8-character state token (WHOOP requirement)
	state = secrets.token_hex(4)  # 4 bytes = 8 hex chars
	
	# Build authorization URL
	params = {
		"client_id": WHOOP_CLIENT_ID,
		"response_type": "code",
		"scope": DEFAULT_SCOPES,
		"redirect_uri": WHOOP_CALLBACK_URL,
		"state": state,
	}
	
	query_string = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
	auth_url = f"{WHOOP_AUTH_URL}?{query_string}"
	
	return auth_url, state


def exchange_code_for_tokens(code: str, user_id: str) -> Dict:
	"""Exchange authorization code for access and refresh tokens.
	
	This implements step 5 of the WHOOP OAuth flow: exchanging the authorization
	code for tokens. Must include 'offline' scope to receive refresh token.
	
	Args:
		code: Authorization code from WHOOP callback
		user_id: The user's UUID from auth.users
		
	Returns:
		Token response dict with access_token, refresh_token, expires_in, etc.
	"""
	supabase = get_supabase()
	
	# Exchange authorization code for tokens
	token_payload = {
		"grant_type": "authorization_code",
		"code": code,
		"redirect_uri": WHOOP_CALLBACK_URL,
		"client_id": WHOOP_CLIENT_ID,
		"client_secret": WHOOP_CLIENT_SECRET,
	}
	
	resp = requests.post(WHOOP_TOKEN_URL, data=token_payload, timeout=15)
	resp.raise_for_status()
	token_data = resp.json()
	
	# Calculate token expiration timestamp
	expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
	
	# Fetch WHOOP user ID from profile endpoint
	whoop_user_id = _get_whoop_user_id(token_data["access_token"])
	
	# Store tokens in database
	supabase.table("whoop").upsert({
		"user_id": user_id,
		"whoop_user_id": whoop_user_id,
		"access_token": token_data["access_token"],
		"refresh_token": token_data["refresh_token"],
		"expires_at": expires_at.isoformat(),
		"updated_at": datetime.now(timezone.utc).isoformat(),
	}).execute()
	
	# Update user's integration flag
	supabase.table("Users").update({"has_whoop": True}).eq("id", user_id).execute()
	
	return token_data


def refresh_access_token(user_id: str) -> Dict:
	"""Refresh expired access token using refresh token.
	
	Per WHOOP docs: Both access_token AND refresh_token are replaced on each refresh.
	The old tokens are invalidated immediately.
	
	Args:
		user_id: User UUID
		
	Returns:
		Updated token data with new access_token and refresh_token
		
	Raises:
		ValueError: If no tokens exist for user
	"""
	supabase = get_supabase()
	token_result = supabase.table("whoop").select("*").eq("user_id", user_id).execute()
	
	if not token_result.data:
		raise ValueError("No WHOOP tokens found for user")
	
	current_refresh_token = token_result.data[0]["refresh_token"]
	
	# Request new tokens using refresh token
	refresh_payload = {
		"grant_type": "refresh_token",
		"refresh_token": current_refresh_token,
		"client_id": WHOOP_CLIENT_ID,
		"client_secret": WHOOP_CLIENT_SECRET,
		"scope": "offline",
	}
	
	resp = requests.post(WHOOP_TOKEN_URL, data=refresh_payload, timeout=15)
	resp.raise_for_status()
	token_data = resp.json()
	
	# Calculate new expiration
	expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
	
	# Update database with new tokens (both access AND refresh are replaced)
	supabase.table("whoop").update({
		"access_token": token_data["access_token"],
		"refresh_token": token_data["refresh_token"],
		"expires_at": expires_at.isoformat(),
		"updated_at": datetime.now(timezone.utc).isoformat(),
	}).eq("user_id", user_id).execute()
	
	return token_data


def get_valid_access_token(user_id: str) -> str:
	"""Get valid access token, automatically refreshing if expired or close to expiry.
	
	Checks token expiration and refreshes proactively (5 min buffer) to avoid
	race conditions with expired tokens during API calls.
	
	Args:
		user_id: User UUID
		
	Returns:
		Valid access token string ready for API calls
	"""
	supabase = get_supabase()
	token_result = supabase.table("whoop").select("*").eq("user_id", user_id).execute()
	
	if not token_result.data:
		raise ValueError("No WHOOP tokens found for user - OAuth flow required")
	
	token_data = token_result.data[0]
	expires_at_str = token_data["expires_at"].replace("Z", "+00:00")
	expires_at = datetime.fromisoformat(expires_at_str)
	now = datetime.now(timezone.utc)
	
	# Refresh if token expires within 5 minutes (safety buffer)
	if now + timedelta(minutes=5) >= expires_at:
		refresh_access_token(user_id)
		# Re-fetch updated token
		token_result = supabase.table("whoop").select("*").eq("user_id", user_id).execute()
		return token_result.data[0]["access_token"]
	
	return token_data["access_token"]


def fetch_cycles(user_id: str, days: int = 14) -> Dict:
	"""Fetch WHOOP cycle data (recovery, strain, sleep) for the specified time period.
	
	Args:
		user_id: User UUID
		days: Number of days to fetch (default 14)
		
	Returns:
		WHOOP cycles API response containing recovery, strain, and sleep data
	"""
	access_token = get_valid_access_token(user_id)
	
	now_utc = datetime.now(timezone.utc)
	start_utc = now_utc - timedelta(days=days)
	params = {
		"start": start_utc.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z"),
		"end": now_utc.isoformat().replace("+00:00", "Z"),
	}
	resp = requests.get(
		f"{WHOOP_API_HOSTNAME}/developer/v2/cycle",
		params=params,
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=15,
	)
	if resp.status_code == 404:
		return {"records": []}
	resp.raise_for_status()
	return resp.json()


def backfill_cycles(user_id: str, days: int = 30) -> Dict[str, int]:
	"""Backfill WHOOP cycle data for the past N days into Supabase.
	
	Args:
		user_id: Supabase user UUID.
		days: Number of days of history to pull (default 30).
	
	Returns:
		Dictionary summarizing number of records fetched and upserted.
	"""
	access_token = get_valid_access_token(user_id)
	start = datetime.now(timezone.utc) - timedelta(days=days)
	start_iso = start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
	params = {"start": start_iso}
	print(f"[backfill_cycles] start user={user_id} days={days} params={params}")
	records = _fetch_paginated_records(access_token, "cycle", params)
	print(f"[backfill_cycles] fetched {len(records)} records")
	if not records:
		return {"fetched": 0, "upserted": 0}
	rows = [_map_cycle_record(user_id, record) for record in records]
	rows = _dedupe_rows(rows, "whoop_cycle_id", log_label="cycles")
	print(f"[backfill_cycles] mapped {len(rows)} rows (sample ids={[row['whoop_cycle_id'] for row in rows[:5]]})")
	supabase = get_supabase()
	upsert_resp = supabase.table("whoop_cycles").upsert(rows, on_conflict="whoop_cycle_id").execute()
	print(f"[backfill_cycles] upserted rows response error={getattr(upsert_resp, 'error', None)} count={len(rows)}")
	return {"fetched": len(records), "upserted": len(rows)}


def _fetch_paginated_records(access_token: str, resource: str, params: Dict) -> List[Dict]:
	"""Fetch WHOOP records handling pagination via next_token."""
	all_records: List[Dict] = []
	next_token = None
	while True:
		query = dict(params)
		if next_token:
			query["nextToken"] = next_token
		resp = requests.get(
			f"{WHOOP_API_HOSTNAME}/developer/v2/{resource}",
			params=query,
			headers={"Authorization": f"Bearer {access_token}"},
			timeout=15,
		)
		if resp.status_code == 404:
			print(f"[fetch_paginated] WHOOP returned 404 for resource={resource} params={query}")
			break
		resp.raise_for_status()
		data = resp.json()
		records = data.get("records", [])
		all_records.extend(records)
		next_token = data.get("next_token")
		if not next_token:
			break
	return all_records


def _map_cycle_record(user_id: str, record: Dict) -> Dict:
	"""Transform WHOOP cycle payload into Supabase row shape."""
	score = record.get("score") or {}
	now_iso = datetime.now(timezone.utc).isoformat()
	return {
		"user_id": user_id,
		"whoop_cycle_id": str(record.get("id")),
		"cycle_start": record.get("start"),
		"cycle_end": record.get("end"),
		"strain": score.get("strain"),
		"average_heart_rate": score.get("average_heart_rate"),
		"max_heart_rate": score.get("max_heart_rate"),
		"kilojoule": score.get("kilojoule"),
		"raw_data": record,
		"synced_at": now_iso,
		"created_at": now_iso,
	}


def backfill_recoveries(user_id: str, days: int = 30) -> Dict[str, int]:
	"""Backfill WHOOP recovery data for the past N days into Supabase."""
	access_token = get_valid_access_token(user_id)
	start = datetime.now(timezone.utc) - timedelta(days=days)
	start_iso = start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
	params = {"start": start_iso}
	print(f"[backfill_recoveries] start user={user_id} days={days} params={params}")
	records = _fetch_paginated_records(access_token, "recovery", params)
	print(f"[backfill_recoveries] fetched {len(records)} records")
	filtered = [record for record in records if record.get("cycle_id") is not None]
	if len(filtered) != len(records):
		print(f"[backfill_recoveries] skipped {len(records) - len(filtered)} records missing cycle_id")
	if not filtered:
		return {"fetched": len(records), "upserted": 0}
	rows = [_map_recovery_record(user_id, record) for record in filtered]
	rows = _dedupe_rows(rows, "whoop_cycle_id", log_label="recoveries")
	print(f"[backfill_recoveries] mapped {len(rows)} rows (sample cycle_ids={[row['whoop_cycle_id'] for row in rows[:5]]})")
	supabase = get_supabase()
	upsert_resp = supabase.table("whoop_recoveries").upsert(rows, on_conflict="whoop_cycle_id").execute()
	print(f"[backfill_recoveries] upsert response error={getattr(upsert_resp, 'error', None)} count={len(rows)}")
	return {"fetched": len(records), "upserted": len(rows)}


def _map_recovery_record(user_id: str, record: Dict) -> Dict:
	score = record.get("score") or {}
	now_iso = datetime.now(timezone.utc).isoformat()
	return {
		"user_id": user_id,
		"whoop_cycle_id": str(record.get("cycle_id")),
		"score_state": record.get("score_state"),
		"recovery_score": score.get("recovery_score"),
		"resting_heart_rate": score.get("resting_heart_rate"),
		"hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
		"spo2_percentage": score.get("spo2_percentage"),
		"skin_temp_celsius": score.get("skin_temp_celsius"),
		"raw_data": record,
		"synced_at": now_iso,
		"created_at": now_iso,
	}


def backfill_sleep(user_id: str, days: int = 30) -> Dict[str, int]:
	"""Backfill WHOOP sleep sessions for the past N days into Supabase."""
	access_token = get_valid_access_token(user_id)
	start = datetime.now(timezone.utc) - timedelta(days=days)
	start_iso = start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
	params = {"start": start_iso}
	print(f"[backfill_sleep] start user={user_id} days={days} params={params}")
	records = _fetch_paginated_records(access_token, "activity/sleep", params)
	print(f"[backfill_sleep] fetched {len(records)} records")
	if not records:
		return {"fetched": 0, "upserted": 0}
	rows = [_map_sleep_record(user_id, record) for record in records]
	rows = _dedupe_rows(rows, "whoop_sleep_id", log_label="sleep")
	print(f"[backfill_sleep] mapped {len(rows)} rows (sample sleep_ids={[row['whoop_sleep_id'] for row in rows[:5]]})")
	supabase = get_supabase()
	upsert_resp = supabase.table("whoop_sleep").upsert(rows, on_conflict="whoop_sleep_id").execute()
	print(f"[backfill_sleep] upsert response error={getattr(upsert_resp, 'error', None)} count={len(rows)}")
	return {"fetched": len(records), "upserted": len(rows)}


def _map_sleep_record(user_id: str, record: Dict) -> Dict:
	score = record.get("score") or {}
	stage_summary = score.get("stage_summary") or {}
	now_iso = datetime.now(timezone.utc).isoformat()
	return {
		"user_id": user_id,
		"whoop_sleep_id": record.get("id"),
		"whoop_cycle_id": str(record.get("cycle_id")) if record.get("cycle_id") is not None else None,
		"start_time": record.get("start"),
		"end_time": record.get("end"),
		"nap": bool(record.get("nap")),
		"score_state": record.get("score_state"),
		"sleep_performance_percentage": score.get("sleep_performance_percentage"),
		"respiratory_rate": score.get("respiratory_rate"),
		"light_sleep_milli": stage_summary.get("total_light_sleep_time_milli"),
		"slow_wave_sleep_milli": stage_summary.get("total_slow_wave_sleep_time_milli"),
		"rem_sleep_milli": stage_summary.get("total_rem_sleep_time_milli"),
		"raw_data": record,
		"synced_at": now_iso,
		"created_at": now_iso,
	}


def backfill_workouts(user_id: str, days: int = 30) -> Dict[str, int]:
	"""Backfill WHOOP workout sessions for the past N days into Supabase."""
	access_token = get_valid_access_token(user_id)
	start = datetime.now(timezone.utc) - timedelta(days=days)
	start_iso = start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
	params = {"start": start_iso}
	print(f"[backfill_workouts] start user={user_id} days={days} params={params}")
	records = _fetch_paginated_records(access_token, "activity/workout", params)
	print(f"[backfill_workouts] fetched {len(records)} records")
	if not records:
		return {"fetched": 0, "upserted": 0}
	rows = [_map_workout_record(user_id, record) for record in records]
	rows = _dedupe_rows(rows, "whoop_workout_id", log_label="workouts")
	print(f"[backfill_workouts] mapped {len(rows)} rows (sample workout_ids={[row['whoop_workout_id'] for row in rows[:5]]})")
	supabase = get_supabase()
	upsert_resp = supabase.table("whoop_workouts").upsert(rows, on_conflict="whoop_workout_id").execute()
	print(f"[backfill_workouts] upsert response error={getattr(upsert_resp, 'error', None)} count={len(rows)}")
	return {"fetched": len(records), "upserted": len(rows)}


def _map_workout_record(user_id: str, record: Dict) -> Dict:
	score = record.get("score") or {}
	zone_durations = (score.get("zone_durations") or {}) if isinstance(score, dict) else {}
	now_iso = datetime.now(timezone.utc).isoformat()
	return {
		"user_id": user_id,
		"whoop_workout_id": record.get("id"),
		"start_time": record.get("start"),
		"end_time": record.get("end"),
		"sport_name": record.get("sport_name"),
		"score_state": record.get("score_state"),
		"strain": score.get("strain"),
		"average_heart_rate": score.get("average_heart_rate"),
		"max_heart_rate": score.get("max_heart_rate"),
		"kilojoule": score.get("kilojoule"),
		"zone_zero_milli": zone_durations.get("zone_zero_milli"),
		"zone_one_milli": zone_durations.get("zone_one_milli"),
		"zone_two_milli": zone_durations.get("zone_two_milli"),
		"zone_three_milli": zone_durations.get("zone_three_milli"),
		"zone_four_milli": zone_durations.get("zone_four_milli"),
		"zone_five_milli": zone_durations.get("zone_five_milli"),
		"raw_data": record,
		"synced_at": now_iso,
		"created_at": now_iso,
	}


def _dedupe_rows(rows: List[Dict], key: str, *, log_label: str = "") -> List[Dict]:
	"""Ensure rows are unique by the provided key for Supabase upsert."""
	deduped: Dict[str, Dict] = {}
	for row in rows:
		value = row.get(key)
		if value is None:
			deduped[f"_none_{id(row)}"] = row
		else:
			deduped[str(value)] = row
	if len(deduped) != len(rows):
		print(
			f"[dedupe] removed {len(rows) - len(deduped)} duplicate rows for key={key}"
			f"{' resource=' + log_label if log_label else ''}"
		)
	return list(deduped.values())


def _get_whoop_user_id(access_token: str) -> str:
	"""Fetch WHOOP user profile to get the unique WHOOP user ID.
	
	Internal helper function.
	
	Args:
		access_token: Valid WHOOP access token
		
	Returns:
		WHOOP user ID string
	"""
	resp = requests.get(
		f"{WHOOP_API_HOSTNAME}/developer/v2/user/profile/basic",
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=15,
	)
	resp.raise_for_status()
	return str(resp.json()["user_id"])
