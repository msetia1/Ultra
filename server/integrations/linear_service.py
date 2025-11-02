"""Linear OAuth 2.0 integration service.

Implements the full OAuth flow per Linear documentation:
https://linear.app/docs/graphql/oauth
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional, Any
import requests
from dotenv import load_dotenv

from integrations.supabase_service import get_supabase

load_dotenv()

# Linear OAuth configuration from environment
LINEAR_CLIENT_ID = os.environ["LINEAR_CLIENT_ID"]
LINEAR_CLIENT_SECRET = os.environ["LINEAR_CLIENT_SECRET"]
LINEAR_CALLBACK_URL = os.environ.get("LINEAR_CALLBACK_URL", "http://localhost:8000/auth/linear/callback")

# Linear API endpoints
LINEAR_AUTH_URL = "https://linear.app/oauth/authorize"
LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

# Scopes for accessing Linear data
DEFAULT_SCOPES = "read,write,issues:create"


def build_authorization_url(user_id: str) -> Tuple[str, str]:
	"""Generate Linear OAuth authorization URL.

	Args:
		user_id: The user's UUID from auth.users

	Returns:
		Tuple of (authorization_url, state_token)
	"""
	# Generate secure state token for CSRF protection
	state = secrets.token_urlsafe(32)

	# Build authorization URL
	params = {
		"client_id": LINEAR_CLIENT_ID,
		"redirect_uri": LINEAR_CALLBACK_URL,
		"response_type": "code",
		"scope": DEFAULT_SCOPES,
		"state": state,
	}

	query_string = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
	auth_url = f"{LINEAR_AUTH_URL}?{query_string}"

	return auth_url, state


def exchange_code_for_tokens(code: str, user_id: str) -> Dict:
	"""Exchange authorization code for access and refresh tokens.

	This implements the Linear OAuth token exchange flow. Linear tokens
	expire after 24 hours and must be refreshed using the refresh token.

	Args:
		code: Authorization code from Linear callback
		user_id: The user's UUID from auth.users

	Returns:
		Token response dict with access_token, refresh_token, expires_in, scope
	"""
	supabase = get_supabase()

	# Exchange authorization code for tokens
	token_payload = {
		"grant_type": "authorization_code",
		"code": code,
		"redirect_uri": LINEAR_CALLBACK_URL,
		"client_id": LINEAR_CLIENT_ID,
		"client_secret": LINEAR_CLIENT_SECRET,
	}

	resp = requests.post(LINEAR_TOKEN_URL, data=token_payload, timeout=15)
	resp.raise_for_status()
	token_data = resp.json()

	# Calculate token expiration timestamp (Linear tokens last 24 hours)
	expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

	# Fetch Linear user info via GraphQL viewer query
	linear_user = _get_linear_user(token_data["access_token"])

	# Store tokens in database
	supabase.table("linear_auth").upsert({
		"user_id": user_id,
		"linear_user_id": linear_user["id"],
		"access_token": token_data["access_token"],
		"refresh_token": token_data["refresh_token"],
		"expires_at": expires_at.isoformat(),
		"updated_at": datetime.now(timezone.utc).isoformat(),
	}).execute()

	# Update user's integration flag
	supabase.table("Users").update({"has_linear": True}).eq("id", user_id).execute()

	return token_data


def refresh_access_token(user_id: str) -> Dict:
	"""Refresh expired access token using refresh token.

	Per Linear docs: Both access_token AND refresh_token are replaced on each refresh.
	The old tokens are invalidated immediately.

	Args:
		user_id: User UUID

	Returns:
		Updated token data with new access_token and refresh_token

	Raises:
		ValueError: If no tokens exist for user
	"""
	supabase = get_supabase()
	token_result = supabase.table("linear_auth").select("*").eq("user_id", user_id).execute()

	if not token_result.data:
		raise ValueError("No Linear tokens found for user")

	current_refresh_token = token_result.data[0]["refresh_token"]

	# Request new tokens using refresh token
	refresh_payload = {
		"grant_type": "refresh_token",
		"refresh_token": current_refresh_token,
		"client_id": LINEAR_CLIENT_ID,
		"client_secret": LINEAR_CLIENT_SECRET,
	}

	resp = requests.post(LINEAR_TOKEN_URL, data=refresh_payload, timeout=15)
	resp.raise_for_status()
	token_data = resp.json()

	# Calculate new expiration
	expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

	# Update database with new tokens (both access AND refresh are replaced)
	supabase.table("linear_auth").update({
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
		Valid access token string ready for GraphQL requests
	"""
	supabase = get_supabase()
	token_result = supabase.table("linear_auth").select("*").eq("user_id", user_id).execute()

	if not token_result.data:
		raise ValueError("No Linear tokens found for user - OAuth flow required")

	token_data = token_result.data[0]
	expires_at_str = token_data["expires_at"].replace("Z", "+00:00")
	expires_at = datetime.fromisoformat(expires_at_str)
	now = datetime.now(timezone.utc)

	# Refresh if token expires within 5 minutes (safety buffer)
	if now + timedelta(minutes=5) >= expires_at:
		refresh_access_token(user_id)
		# Re-fetch updated token
		token_result = supabase.table("linear_auth").select("*").eq("user_id", user_id).execute()
		return token_result.data[0]["access_token"]

	return token_data["access_token"]


def execute_graphql_query(query: str, variables: Optional[Dict] = None, access_token: Optional[str] = None) -> Dict:
	"""Execute a GraphQL query against Linear API.

	Args:
		query: GraphQL query string
		variables: Optional variables for the query
		access_token: Linear access token for authorization

	Returns:
		GraphQL response data

	Raises:
		requests.HTTPError: If request fails
		ValueError: If GraphQL returns errors
	"""
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {access_token}",
	}

	payload = {"query": query}
	if variables:
		payload["variables"] = variables

	resp = requests.post(LINEAR_GRAPHQL_URL, json=payload, headers=headers, timeout=15)
	resp.raise_for_status()

	result = resp.json()

	# Check for GraphQL errors
	if "errors" in result:
		error_messages = [error.get("message", "Unknown error") for error in result["errors"]]
		raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")

	return result.get("data", {})


def fetch_teams(user_id: str) -> Dict:
	"""Fetch all teams the user has access to.

	Args:
		user_id: User UUID

	Returns:
		Teams data from Linear API
	"""
	access_token = get_valid_access_token(user_id)

	query = """
	query Teams {
		teams {
			nodes {
				id
				name
				key
				description
				icon
				color
			}
		}
	}
	"""

	data = execute_graphql_query(query, access_token=access_token)
	return data.get("teams", {})


def fetch_issues(
	user_id: str,
	team_id: Optional[str] = None,
	filters: Optional[Dict[str, Any]] = None,
	first: int = 50
) -> Dict:
	"""Fetch Linear issues with optional filtering and pagination.

	Args:
		user_id: User UUID
		team_id: Optional team ID to filter by
		filters: Optional filters (assignee, state, priority, etc.)
		first: Number of issues to fetch (default 50)

	Returns:
		Issues data from Linear API
	"""
	access_token = get_valid_access_token(user_id)

	# Build filter object for GraphQL
	graphql_filter = {}
	if team_id:
		graphql_filter["team"] = {"id": {"eq": team_id}}

	if filters:
		# Handle assignee filter ("me" or user ID)
		if filters.get("assignee") == "me":
			# Need to get current user ID first
			viewer_data = execute_graphql_query("query { viewer { id } }", access_token=access_token)
			viewer_id = viewer_data.get("viewer", {}).get("id")
			if viewer_id:
				graphql_filter["assignee"] = {"id": {"eq": viewer_id}}
		elif filters.get("assignee"):
			graphql_filter["assignee"] = {"id": {"eq": filters["assignee"]}}

		# Handle state type filter (backlog, started, completed, canceled)
		if filters.get("state"):
			graphql_filter["state"] = {"type": {"eq": filters["state"]}}

		# Handle priority filter
		if filters.get("priority") is not None:
			graphql_filter["priority"] = {"eq": filters["priority"]}

	query = """
	query Issues($first: Int!, $filter: IssueFilter) {
		issues(first: $first, filter: $filter) {
			nodes {
				id
				identifier
				title
				description
				priority
				state {
					id
					name
					type
				}
				assignee {
					id
					name
					email
				}
				team {
					id
					name
					key
				}
				project {
					id
					name
				}
				dueDate
				createdAt
				updatedAt
				completedAt
				canceledAt
			}
			pageInfo {
				hasNextPage
				endCursor
			}
		}
	}
	"""

	variables = {
		"first": first,
		"filter": graphql_filter if graphql_filter else None,
	}

	data = execute_graphql_query(query, variables=variables, access_token=access_token)
	return data.get("issues", {})


def fetch_projects(user_id: str) -> Dict:
	"""Fetch active projects.

	Args:
		user_id: User UUID

	Returns:
		Projects data from Linear API
	"""
	access_token = get_valid_access_token(user_id)

	query = """
	query Projects {
		projects {
			nodes {
				id
				name
				description
				state
				progress
				startedAt
				targetDate
				completedAt
				lead {
					id
					name
				}
			}
		}
	}
	"""

	data = execute_graphql_query(query, access_token=access_token)
	return data.get("projects", {})


def create_issue(
	user_id: str,
	team_id: str,
	title: str,
	description: Optional[str] = None,
	priority: Optional[int] = None,
	assignee_id: Optional[str] = None,
	state_id: Optional[str] = None,
	project_id: Optional[str] = None,
) -> Dict:
	"""Create a new Linear issue.

	Args:
		user_id: User UUID
		team_id: Team ID where issue will be created
		title: Issue title
		description: Optional issue description (supports markdown)
		priority: Optional priority (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low)
		assignee_id: Optional assignee user ID
		state_id: Optional workflow state ID
		project_id: Optional project ID

	Returns:
		Created issue data from Linear API
	"""
	access_token = get_valid_access_token(user_id)

	# Build input object
	issue_input = {
		"teamId": team_id,
		"title": title,
	}

	if description:
		issue_input["description"] = description
	if priority is not None:
		issue_input["priority"] = priority
	if assignee_id:
		issue_input["assigneeId"] = assignee_id
	if state_id:
		issue_input["stateId"] = state_id
	if project_id:
		issue_input["projectId"] = project_id

	mutation = """
	mutation IssueCreate($input: IssueCreateInput!) {
		issueCreate(input: $input) {
			success
			issue {
				id
				identifier
				title
				description
				priority
				state {
					id
					name
				}
				assignee {
					id
					name
				}
			}
		}
	}
	"""

	variables = {"input": issue_input}

	data = execute_graphql_query(mutation, variables=variables, access_token=access_token)
	issue_create_result = data.get("issueCreate", {})

	if not issue_create_result.get("success"):
		raise ValueError("Failed to create Linear issue")

	return issue_create_result.get("issue", {})


def _get_linear_user(access_token: str) -> Dict:
	"""Fetch Linear user profile to get the unique Linear user ID.

	Internal helper function.

	Args:
		access_token: Valid Linear access token

	Returns:
		User data with id, name, email
	"""
	query = """
	query Me {
		viewer {
			id
			name
			email
		}
	}
	"""

	data = execute_graphql_query(query, access_token=access_token)
	return data.get("viewer", {})
