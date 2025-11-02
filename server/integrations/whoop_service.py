"""WHOOP OAuth 2.0 integration service.

Implements the full OAuth flow per WHOOP documentation:
https://developer.whoop.com/docs/developing/oauth/
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Tuple
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
DEFAULT_SCOPES = "offline read:recovery read:workout read:sleep read:cycle read:profile"


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
	expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
	
	# Fetch WHOOP user ID from profile endpoint
	whoop_user_id = _get_whoop_user_id(token_data["access_token"])
	
	# Store tokens in database
	supabase.table("whoop").upsert({
		"user_id": user_id,
		"whoop_user_id": whoop_user_id,
		"access_token": token_data["access_token"],
		"refresh_token": token_data["refresh_token"],
		"expires_at": expires_at.isoformat(),
		"updated_at": datetime.utcnow().isoformat(),
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
	expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
	
	# Update database with new tokens (both access AND refresh are replaced)
	supabase.table("whoop").update({
		"access_token": token_data["access_token"],
		"refresh_token": token_data["refresh_token"],
		"expires_at": expires_at.isoformat(),
		"updated_at": datetime.utcnow().isoformat(),
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
	
	# Refresh if token expires within 5 minutes (safety buffer)
	if datetime.utcnow() + timedelta(minutes=5) >= expires_at:
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
	
	end_date = datetime.utcnow().date()
	start_date = end_date - timedelta(days=days)
	
	resp = requests.get(
		f"{WHOOP_API_HOSTNAME}/developer/v1/cycle",
		params={"start": start_date.isoformat(), "end": end_date.isoformat()},
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=15,
	)
	resp.raise_for_status()
	return resp.json()


def _get_whoop_user_id(access_token: str) -> str:
	"""Fetch WHOOP user profile to get the unique WHOOP user ID.
	
	Internal helper function.
	
	Args:
		access_token: Valid WHOOP access token
		
	Returns:
		WHOOP user ID string
	"""
	resp = requests.get(
		f"{WHOOP_API_HOSTNAME}/developer/v1/user/profile/basic",
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=15,
	)
	resp.raise_for_status()
	return str(resp.json()["user_id"])

