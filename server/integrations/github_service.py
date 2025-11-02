"""GitHub integration helpers."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from integrations.supabase_service import get_supabase

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
VIEWER_QUERY = """
query {
  viewer {
    id
    login
    name
    avatarUrl
    url
  }
}
"""

RECENT_COMMITS_QUERY = """
query RecentCommits($owner: String!, $name: String!, $ref: String!, $limit: Int!, $since: GitTimestamp, $viewerId: ID!) {
  repository(owner: $owner, name: $name) {
    ref(qualifiedName: $ref) {
      name
      target {
        ... on Commit {
          history(first: $limit, since: $since, author: {id: $viewerId}) {
            nodes {
              oid
              authoredDate
              committedDate
              messageHeadline
              messageBody
              additions
              deletions
              repository {
                nameWithOwner
              }
            }
          }
        }
      }
    }
  }
}
"""

VIEWER_ID_QUERY = """
query {
  viewer {
    id
  }
}
"""

VIEWER_REPOSITORIES_QUERY = """
query ViewerRepositories($first: Int!, $after: String, $affiliations: [RepositoryAffiliation!], $orderField: RepositoryOrderField!, $orderDirection: OrderDirection!) {
  viewer {
    repositories(first: $first, after: $after, affiliations: $affiliations, orderBy: {field: $orderField, direction: $orderDirection}) {
      nodes {
        nameWithOwner
        description
        isPrivate
        isFork
        defaultBranchRef {
          name
        }
        pushedAt
        updatedAt
        url
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
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


def fetch_recent_commits(
	user_id: str,
	repo_full_name: str,
	branch: str = "main",
	limit: int = 20,
	since: Optional[datetime] = None,
) -> Dict[str, int]:
	"""Fetch recent commits for a repository and persist them."""
	access_token, _ = _get_github_credentials(user_id)
	viewer_id = _get_viewer_id(access_token)
	owner, name = _split_full_name(repo_full_name)
	variables = {
		"owner": owner,
		"name": name,
		"ref": f"refs/heads/{branch}",
		"limit": limit,
		"since": since.isoformat() if since else None,
		"viewerId": viewer_id,
	}
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Accept": "application/vnd.github+json",
	}
	resp = requests.post(
		GITHUB_GRAPHQL_URL,
		json={"query": RECENT_COMMITS_QUERY, "variables": variables},
		headers=headers,
		timeout=15,
	)
	resp.raise_for_status()
	payload = resp.json()

	if "errors" in payload:
		message = payload["errors"][0].get("message", "Unknown GitHub error")
		raise ValueError(f"GitHub API error: {message}")

	repository = payload["data"]["repository"]
	if not repository or not repository.get("ref"):
		raise ValueError(f"Branch '{branch}' not found for repository {repo_full_name}")

	history = repository["ref"]["target"].get("history") if repository["ref"]["target"] else None
	if not history:
		return {"fetched": 0, "upserted": 0}

	nodes: List[Dict] = history.get("nodes") or []
	if not nodes:
		return {"fetched": 0, "upserted": 0}

	now_iso = datetime.now(timezone.utc).isoformat()
	commit_rows = [
		_map_commit_node(user_id, repo_full_name, branch, node, now_iso) for node in nodes
	]

	supabase = get_supabase()
	supabase.table("github_commits").upsert(commit_rows, on_conflict="sha").execute()

	supabase.table("github_integrations").update({"last_synced_at": now_iso}).eq("user_id", user_id).execute()

	return {"fetched": len(nodes), "upserted": len(commit_rows)}


def list_repositories(
	user_id: str,
	first: int = 20,
	after: Optional[str] = None,
	include_org_memberships: bool = False,
) -> Dict[str, Any]:
	"""Return repositories the authenticated user can access for selection."""
	access_token, github_login = _get_github_credentials(user_id)
	affiliations = ["OWNER", "COLLABORATOR"]
	if include_org_memberships:
		affiliations.append("ORGANIZATION_MEMBER")

	variables = {
		"first": first,
		"after": after,
		"affiliations": affiliations,
		"orderField": "PUSHED_AT",
		"orderDirection": "DESC",
	}
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Accept": "application/vnd.github+json",
	}
	resp = requests.post(
		GITHUB_GRAPHQL_URL,
		json={"query": VIEWER_REPOSITORIES_QUERY, "variables": variables},
		headers=headers,
		timeout=15,
	)
	resp.raise_for_status()
	payload = resp.json()

	if "errors" in payload:
		message = payload["errors"][0].get("message", "Unknown GitHub error")
		raise ValueError(f"GitHub API error: {message}")

	viewer = payload.get("data", {}).get("viewer")
	if not viewer:
		raise ValueError("GitHub API error: viewer information unavailable")

	repos = viewer.get("repositories") or {}
	nodes = repos.get("nodes") or []
	page_info = repos.get("pageInfo") or {}

	items = []
	for node in nodes:
		default_branch = None
		if node.get("defaultBranchRef"):
			default_branch = node["defaultBranchRef"].get("name")
		items.append({
			"repo_full_name": node.get("nameWithOwner"),
			"description": node.get("description"),
			"default_branch": default_branch,
			"is_private": node.get("isPrivate"),
			"is_fork": node.get("isFork"),
			"pushed_at": node.get("pushedAt"),
			"updated_at": node.get("updatedAt"),
			"url": node.get("url"),
		})

	return {
		"user_login": github_login,
		"items": items,
		"page_info": {
			"has_next_page": page_info.get("hasNextPage"),
			"end_cursor": page_info.get("endCursor"),
		},
		"total_count": repos.get("totalCount"),
	}


def _get_github_credentials(user_id: str) -> Tuple[str, str]:
	"""Look up stored GitHub PAT and login for the given user."""
	supabase = get_supabase()
	result = supabase.table("github_integrations").select("access_token, github_login").eq("user_id", user_id).execute()
	if not result.data:
		raise ValueError("GitHub integration not connected for user")
	record = result.data[0]
	return record["access_token"], record["github_login"]


def _get_viewer_id(access_token: str) -> str:
	"""Fetch the authenticated viewer's node ID."""
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Accept": "application/vnd.github+json",
	}
	resp = requests.post(
		GITHUB_GRAPHQL_URL,
		json={"query": VIEWER_ID_QUERY},
		headers=headers,
		timeout=10,
	)
	resp.raise_for_status()
	payload = resp.json()

	if "errors" in payload:
		message = payload["errors"][0].get("message", "Unknown GitHub error")
		raise ValueError(f"GitHub API error: {message}")

	viewer = payload.get("data", {}).get("viewer")
	if not viewer:
		raise ValueError("GitHub API error: viewer information unavailable")

	return viewer["id"]


def _split_full_name(repo_full_name: str) -> Tuple[str, str]:
	if "/" not in repo_full_name:
		raise ValueError("Repository full name must be in the format owner/name")
	return tuple(repo_full_name.split("/", 1))  # type: ignore[return-value]


def _map_commit_node(user_id: str, repo_full_name: str, branch: str, node: Dict, now_iso: str) -> Dict:
	return {
		"sha": node["oid"],
		"user_id": user_id,
		"repo_full_name": repo_full_name,
		"branch": branch,
		"authored_at": node.get("authoredDate"),
		"committed_at": node.get("committedDate"),
		"message_headline": node.get("messageHeadline"),
		"message_body": node.get("messageBody"),
		"additions": node.get("additions"),
		"deletions": node.get("deletions"),
		"total_changes": _calculate_total_changes(node),
		"raw_payload": node,
		"created_at": now_iso,
		"updated_at": now_iso,
	}


def _calculate_total_changes(node: Dict) -> Optional[int]:
	additions = node.get("additions")
	deletions = node.get("deletions")
	if additions is None or deletions is None:
		return None
	return additions + deletions
