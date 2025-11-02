"""GitHub integration helpers."""

from datetime import datetime, timezone
from typing import Dict

import requests

from integrations.supabase_service import get_supabase

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
VIEWER_QUERY = """
query {
  viewer {
    login
    name
    avatarUrl
    url
  }
}
"""


def connect_github(user_id: str, personal_access_token: str) -> Dict[str, str]:
	"""Validate PAT with GitHub and persist credentials + profile metadata."""
	if not personal_access_token:
		raise ValueError("Personal access token is required")

	headers = {
		"Authorization": f"Bearer {personal_access_token}",
		"Accept": "application/vnd.github+json",
	}
	response = requests.post(
		GITHUB_GRAPHQL_URL,
		json={"query": VIEWER_QUERY},
		headers=headers,
		timeout=10,
	)
	response.raise_for_status()
	payload = response.json()

	if "errors" in payload:
		message = payload["errors"][0].get("message", "Unknown GitHub error")
		raise ValueError(f"GitHub API error: {message}")

	viewer = payload["data"]["viewer"]
	now_iso = datetime.now(timezone.utc).isoformat()

	supabase = get_supabase()

	supabase.table("github_integrations").upsert({
		"user_id": user_id,
		"github_login": viewer["login"],
		"access_token": personal_access_token,
		"avatar_url": viewer["avatarUrl"],
		"profile_url": viewer["url"],
		"last_synced_at": now_iso,
		"updated_at": now_iso,
	}).execute()

	supabase.table("Users").update({"has_github": True}).eq("id", user_id).execute()

	return {
		"login": viewer["login"],
		"name": viewer["name"],
		"avatar_url": viewer["avatarUrl"],
		"profile_url": viewer["url"],
	}
