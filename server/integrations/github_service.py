"""GitHub integration helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from integrations.supabase_service import get_supabase

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
GITHUB_REST_BASE = "https://api.github.com"
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
query RecentCommits($owner: String!, $name: String!, $ref: String!, $limit: Int!, $cursor: String, $since: GitTimestamp, $viewerId: ID!) {
  repository(owner: $owner, name: $name) {
    ref(qualifiedName: $ref) {
      name
      target {
        ... on Commit {
          history(first: $limit, after: $cursor, since: $since, author: {id: $viewerId}) {
            pageInfo {
              hasNextPage
              endCursor
            }
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
	limit: Optional[int] = None,
	since: Optional[datetime] = None,
) -> Dict[str, int]:
	"""Fetch commits for a repository (optionally limited) and persist them."""
	access_token, _ = _get_github_credentials(user_id)
	viewer_id = _get_viewer_id(access_token)
	owner, name = _split_full_name(repo_full_name)
	remaining = None if limit is None or limit <= 0 else int(limit)
	cursor: Optional[str] = None
	nodes: List[Dict] = []

	while True:
		if remaining is not None and remaining <= 0:
			break

		current_limit = 100 if remaining is None else min(remaining, 100)
		variables = {
			"owner": owner,
			"name": name,
			"ref": f"refs/heads/{branch}",
			"limit": current_limit,
			"cursor": cursor,
			"since": _format_since_timestamp(since),
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

		target = repository["ref"]["target"]
		history = target.get("history") if target else None
		if not history:
			break

		page_nodes: List[Dict] = history.get("nodes") or []
		if page_nodes:
			nodes.extend(page_nodes)
			if remaining is not None:
				remaining -= len(page_nodes)
				if remaining <= 0:
					break

		page_info = history.get("pageInfo") or {}
		has_next = bool(page_info.get("hasNextPage"))
		cursor = page_info.get("endCursor")

		if not has_next or not cursor:
			break

	now_iso = datetime.now(timezone.utc).isoformat()
	unique_nodes: Dict[str, Dict] = {}
	for node in nodes:
		unique_nodes[node["oid"]] = node

	if not unique_nodes:
		return {"fetched": 0, "upserted": 0}

	commit_rows = [
		_map_commit_node(user_id, repo_full_name, branch, node, now_iso) for node in unique_nodes.values()
	]

	supabase = get_supabase()
	supabase.table("github_commits").upsert(commit_rows, on_conflict="sha").execute()

	supabase.table("github_integrations").update({"last_synced_at": now_iso}).eq("user_id", user_id).execute()

	return {"fetched": len(unique_nodes), "upserted": len(commit_rows)}


def backfill_selected_repositories_commits(
	user_id: str,
	limit_per_repo: Optional[int] = None,
	since_days: Optional[int] = None,
) -> Dict[str, Any]:
	"""Fetch recent commits for repositories the user selected."""
	supabase = get_supabase()
	repo_result = supabase.table("github_repositories").select(
		"repo_full_name, default_branch, include"
	).eq("user_id", user_id).eq("include", True).execute()

	repos = repo_result.data or []
	if not repos:
		return {"processed_repositories": 0, "results": []}

	since_dt = None
	if since_days is not None:
		since_dt = datetime.now(timezone.utc) - timedelta(days=since_days)

	results: List[Dict[str, Any]] = []
	for repo in repos:
		repo_full_name = repo.get("repo_full_name")
		if not repo_full_name:
			continue
		branch = repo.get("default_branch") or "main"
		try:
			result = fetch_recent_commits(
				user_id=user_id,
				repo_full_name=repo_full_name,
				branch=branch,
				limit=limit_per_repo,
				since=since_dt,
			)
			results.append({
				"repo_full_name": repo_full_name,
				"branch": branch,
				**result,
			})
		except ValueError as err:
			results.append({
				"repo_full_name": repo_full_name,
				"branch": branch,
				"error": str(err),
			})
		except Exception as err:  # noqa: BLE001
			results.append({
				"repo_full_name": repo_full_name,
				"branch": branch,
				"error": str(err),
			})

	return {
		"processed_repositories": len(repos),
		"results": results,
	}


def backfill_commit_files(
	user_id: str,
	limit_commits: Optional[int] = None,
) -> Dict[str, Any]:
	"""Fetch per-file details for commits belonging to selected repositories."""
	access_token, _ = _get_github_credentials(user_id)
	supabase = get_supabase()

	selected_repos_result = supabase.table("github_repositories").select(
		"repo_full_name"
	).eq("user_id", user_id).eq("include", True).execute()
	selected_repo_names = {row["repo_full_name"] for row in (selected_repos_result.data or []) if row.get("repo_full_name")}

	query = supabase.table("github_commits").select(
		"sha, repo_full_name, branch"
	).eq("user_id", user_id).is_("files_processed_at", "null")

	if selected_repo_names:
		query = query.in_("repo_full_name", list(selected_repo_names))

	if limit_commits is not None:
		query = query.limit(limit_commits)

	commits_result = query.execute()
	commits = commits_result.data or []

	if not commits:
		return {"processed_commits": 0, "results": []}

	results: List[Dict[str, Any]] = []
	for commit in commits:
		sha = commit["sha"]
		repo_full_name = commit["repo_full_name"]
		owner, name = _split_full_name(repo_full_name)
		now_iso = datetime.now(timezone.utc).isoformat()
		try:
			commit_payload = _fetch_commit_from_rest(access_token, owner, name, sha)
			files = commit_payload.get("files") or []
			file_rows = [_map_commit_file_row(sha, file_data, now_iso) for file_data in files]

			if file_rows:
				supabase.table("github_commit_files").upsert(
					file_rows,
					on_conflict="commit_sha,path",
				).execute()

			supabase.table("github_commits").update({
				"files_processed_at": now_iso,
				"files_processed_error": None,
			}).eq("sha", sha).execute()

			results.append({
				"commit_sha": sha,
				"repo_full_name": repo_full_name,
				"files_count": len(file_rows),
			})
		except Exception as err:  # noqa: BLE001
			error_message = str(err)
			supabase.table("github_commits").update({
				"files_processed_error": error_message,
			}).eq("sha", sha).execute()
			results.append({
				"commit_sha": sha,
				"repo_full_name": repo_full_name,
				"error": error_message,
			})

	return {
		"processed_commits": len(commits),
		"results": results,
	}

def list_repositories(
	user_id: str,
	first: int = 20,
	after: Optional[str] = None,
	include_org_memberships: bool = False,
	fetch_all: bool = False,
) -> Dict[str, Any]:
	"""Return repositories the authenticated user can access for selection."""
	access_token, github_login = _get_github_credentials(user_id)
	affiliations = ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"] if include_org_memberships else ["OWNER", "COLLABORATOR"]

	page_limit = max(1, min(first, 100))
	current_after = after
	all_items: List[Dict[str, Any]] = []
	total_count: Optional[int] = None
	last_page_info: Dict[str, Any] = {}

	while True:
		variables = {
			"first": page_limit,
			"after": current_after,
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
		last_page_info = page_info

		if total_count is None:
			total_count = repos.get("totalCount")

		for node in nodes:
			default_branch = None
			if node.get("defaultBranchRef"):
				default_branch = node["defaultBranchRef"].get("name")
			all_items.append({
				"repo_full_name": node.get("nameWithOwner"),
				"description": node.get("description"),
				"default_branch": default_branch,
				"is_private": node.get("isPrivate"),
				"is_fork": node.get("isFork"),
				"pushed_at": node.get("pushedAt"),
				"updated_at": node.get("updatedAt"),
				"url": node.get("url"),
			})

		has_next_page = bool(page_info.get("hasNextPage"))
		end_cursor = page_info.get("endCursor")

		if fetch_all and has_next_page and end_cursor:
			current_after = end_cursor
			continue

		break

	page_info_response = {
		"has_next_page": False if fetch_all else bool(last_page_info.get("hasNextPage")),
		"end_cursor": None if fetch_all else last_page_info.get("endCursor"),
	}

	return {
		"user_login": github_login,
		"items": all_items,
		"page_info": page_info_response,
		"total_count": total_count if total_count is not None else len(all_items),
	}


def upsert_selected_repositories(user_id: str, repositories: List[Dict[str, Any]]) -> Dict[str, int]:
	"""Persist user-selected repositories for syncing."""
	if repositories is None:
		raise ValueError("Repository selection payload is required")

	rows = []
	now_iso = datetime.now(timezone.utc).isoformat()
	for repo in repositories:
		repo_full_name = repo.get("repo_full_name")
		if not repo_full_name:
			raise ValueError("Each repository entry must include 'repo_full_name'")
		include = repo.get("include", True)
		rows.append({
			"user_id": user_id,
			"repo_full_name": repo_full_name,
			"default_branch": repo.get("default_branch"),
			"include": bool(include),
			"raw_payload": repo.get("raw_payload"),
			"updated_at": now_iso,
			"created_at": now_iso,
		})

	if not rows:
		return {"upserted": 0}

	supabase = get_supabase()
	supabase.table("github_repositories").upsert(rows, on_conflict="user_id,repo_full_name").execute()

	return {"upserted": len(rows)}


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


def _format_since_timestamp(since: Optional[datetime]) -> Optional[str]:
	if not since:
		return None
	normalized = since.astimezone(timezone.utc)
	return normalized.isoformat().replace("+00:00", "Z")


def _fetch_commit_from_rest(access_token: str, owner: str, name: str, sha: str) -> Dict[str, Any]:
	url = f"{GITHUB_REST_BASE}/repos/{owner}/{name}/commits/{sha}"
	headers = {
		"Authorization": f"Bearer {access_token}",
		"Accept": "application/vnd.github+json",
	}
	resp = requests.get(url, headers=headers, timeout=20)
	resp.raise_for_status()
	return resp.json()


def _map_commit_file_row(commit_sha: str, file_data: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
	return {
		"commit_sha": commit_sha,
		"path": file_data.get("filename"),
		"change_type": file_data.get("status"),
		"additions": file_data.get("additions"),
		"deletions": file_data.get("deletions"),
		"patch": file_data.get("patch"),
		"created_at": now_iso,
		"updated_at": now_iso,
	}


def _format_since_timestamp(since: Optional[datetime]) -> Optional[str]:
	if not since:
		return None
	normalized = since.astimezone(timezone.utc)
	return normalized.isoformat().replace("+00:00", "Z")
