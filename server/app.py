import os
from typing import Optional
from urllib.parse import quote_plus
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from integrations.github_service import (
	connect_github,
	list_repositories,
	backfill_selected_repositories_commits,
	backfill_commit_files,
	upsert_selected_repositories,
	build_authorization_url as build_github_auth_url,
	exchange_code_for_tokens as exchange_github_tokens,
)
from integrations.whoop_service import (
	backfill_cycles,
	backfill_recoveries,
	backfill_sleep,
	backfill_workouts,
	build_authorization_url as build_whoop_auth_url,
	exchange_code_for_tokens as exchange_whoop_tokens,
	fetch_cycles,
)

from integrations.linear_service import (
	build_authorization_url as build_linear_auth_url,
	exchange_code_for_tokens as exchange_linear_tokens,
	fetch_teams,
	fetch_issues,
	fetch_projects,
	create_issue,
)

from routers.calendar.routers import chat_router, accept_router

load_dotenv()

app = FastAPI(title="AI Scheduling Agent API")

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")


def _frontend_redirect(path: str) -> RedirectResponse:
	"""Redirect to the configured frontend base URL."""
	path_with_leading = path if path.startswith("/") else f"/{path}"
	return RedirectResponse(url=f"{FRONTEND_BASE_URL}{path_with_leading}")

# Include calendar routers
app.include_router(chat_router)
app.include_router(accept_router)

# CORS middleware for frontend
# Determine allowed origins based on environment
allowed_origins = [
	"http://localhost:3000",
	"http://localhost:8000",
	"http://127.0.0.1:8000",
]

# Add production domain if in production
if os.getenv("ENVIRONMENT") == "production":
	allowed_origins.extend([
		"https://ultra-calendar.com",
		"https://www.ultra-calendar.com",
	])

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Serve static files from static directory (built frontend)
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
	app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")

# Development user ID - replace with actual user from auth flow
TEST_USER_ID = os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")


@app.get("/")
def root():
	"""Serve the frontend application."""
	static_html = os.path.join(static_path, "index.html")
	if os.path.exists(static_html):
		return FileResponse(static_html)
	return {
		"message": "AI Scheduling Agent API",
		"version": "0.1.0",
		"integrations": {
			"whoop": {
				"start_oauth": "/auth/whoop/start",
				"callback": "/auth/whoop/callback",
				"fetch_cycles": "/whoop/cycles",
			},
			"github": {
				"start_oauth": "/auth/github/start",
				"callback": "/auth/github/callback",
				"list_repositories": "/github/repositories",
				"save_repositories": "/github/repositories",
				"backfill_commits": "/github/backfill",
			},
			"linear": {
				"start_oauth": "/auth/linear/start",
				"callback": "/auth/linear/callback",
				"fetch_teams": "/linear/teams",
				"fetch_issues": "/linear/issues",
				"fetch_projects": "/linear/projects",
				"create_issue": "/linear/issues",
			},
		},
		"status": "operational",
	}


@app.get("/api")
def api_info():
	"""API information endpoint."""
	return {
		"message": "AI Scheduling Agent API",
		"version": "0.1.0",
		"integrations": {
			"whoop": {
				"start_oauth": "/auth/whoop/start",
				"callback": "/auth/whoop/callback",
				"fetch_cycles": "/whoop/cycles",
			},
			"github": {
				"start_oauth": "/auth/github/start",
				"callback": "/auth/github/callback",
				"list_repositories": "/github/repositories",
				"save_repositories": "/github/repositories",
				"backfill_commits": "/github/backfill",
			},
			"linear": {
				"start_oauth": "/auth/linear/start",
				"callback": "/auth/linear/callback",
				"fetch_teams": "/linear/teams",
				"fetch_issues": "/linear/issues",
				"fetch_projects": "/linear/projects",
				"create_issue": "/linear/issues",
			},
		},
		"status": "operational",
	}


@app.get("/auth/github/start")
def start_github_oauth():
	"""Initiate GitHub OAuth flow."""
	try:
		auth_url, _ = build_github_auth_url(TEST_USER_ID)
		return RedirectResponse(url=auth_url)
	except Exception as err:  # noqa: BLE001
		raise HTTPException(status_code=500, detail=f"Error starting GitHub OAuth: {err}") from err


@app.get("/auth/github/callback")
def github_callback(code: str, state: Optional[str] = None):
	"""Handle GitHub OAuth callback."""
	del state  # State validation skipped for hackathon demo.
	try:
		token_data = exchange_github_tokens(code)
		access_token = token_data.get("access_token")
		if not access_token:
			raise ValueError("GitHub OAuth response missing access token")

		connect_github(TEST_USER_ID, access_token)
		return _frontend_redirect("/onboarding?github=connected")
	except Exception as err:  # noqa: BLE001
		error_value = quote_plus(str(err))
		return _frontend_redirect(f"/onboarding?error={error_value}")


@app.get("/auth/whoop/start")
def start_whoop_oauth():
	"""Initiate WHOOP OAuth flow."""
	try:
		auth_url, state = build_whoop_auth_url(TEST_USER_ID)
		return RedirectResponse(url=auth_url)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error starting OAuth: {str(e)}")


@app.get("/auth/whoop/callback")
def whoop_callback(code: str, state: str):
	"""Handle WHOOP OAuth callback."""
	try:
		tokens = exchange_whoop_tokens(code, TEST_USER_ID)
		# Trigger initial cycle backfill for the last month
		try:
			backfill_cycles(TEST_USER_ID, days=30)
			backfill_recoveries(TEST_USER_ID, days=30)
			backfill_sleep(TEST_USER_ID, days=30)
			backfill_workouts(TEST_USER_ID, days=30)
		except Exception as backfill_err:  # noqa: BLE001
			# Log the error but don't block the redirect flow
			print(f"Error during WHOOP backfill: {backfill_err}")
		# Redirect back to frontend with success
		return _frontend_redirect("/onboarding?whoop=connected")
	except Exception as e:
		# Redirect back to frontend with error
		error_value = quote_plus(str(e))
		return _frontend_redirect(f"/onboarding?error={error_value}")


# @app.get("/whoop/cycles")
# def get_whoop_cycles(days: int = 7):
# 	"""Fetch WHOOP cycle data including recovery, strain, and sleep metrics."""
# 	try:
# 		cycles_data = fetch_cycles(TEST_USER_ID, days=days)
# 		return {
# 			"status": "success",
# 			"days_requested": days,
# 			"data": cycles_data,
# 		}
# 	except ValueError as e:
# 		raise HTTPException(
# 			status_code=404,
# 			detail="WHOOP integration not connected. Complete OAuth flow first.",
# 		)
# 	except Exception as e:
# 		raise HTTPException(status_code=500, detail=f"Error fetching cycles: {str(e)}")


@app.get("/github/repositories")
def get_github_repositories(
	first: int = Query(20, ge=1, le=100),
	after: Optional[str] = Query(None),
	include_org: bool = Query(False),
	fetch_all: bool = Query(False),
):
	"""List repositories accessible to the connected GitHub user."""
	try:
		return list_repositories(
			TEST_USER_ID,
			first=first,
			after=after,
			include_org_memberships=include_org,
			fetch_all=fetch_all,
		)
	except ValueError as err:
		raise HTTPException(status_code=400, detail=str(err))
	except Exception as err:  # noqa: BLE001
		raise HTTPException(status_code=500, detail=str(err))


@app.post("/github/repositories")
def save_github_repositories(payload: dict = Body(...)):
	"""Persist user-selected repositories for commit syncing."""
	repositories = (payload or {}).get("repositories")
	try:
		result = upsert_selected_repositories(TEST_USER_ID, repositories)
		return {"status": "ok", **result}
	except ValueError as err:
		raise HTTPException(status_code=400, detail=str(err))
	except Exception as err:  # noqa: BLE001
		raise HTTPException(status_code=500, detail=str(err))


@app.post("/github/backfill")
def backfill_github_commits(payload: Optional[dict] = Body(None)):
	"""Backfill recent commits for repositories the user has selected."""
	body = payload or {}
	limit_raw = body.get("limit_per_repo")
	since_raw = body.get("since_days")
	files_limit_raw = body.get("files_limit")
	limit_per_repo = None
	if limit_raw not in (None, "", "null"):
		try:
			limit_per_repo = int(limit_raw)
		except (TypeError, ValueError) as exc:
			raise HTTPException(status_code=400, detail="limit_per_repo must be an integer or null") from exc

	since_days = None
	if since_raw not in (None, "", "null"):
		try:
			since_days = int(since_raw)
		except (TypeError, ValueError) as exc:
			raise HTTPException(status_code=400, detail="since_days must be an integer or null") from exc

	files_limit = None
	if files_limit_raw not in (None, "", "null"):
		try:
			files_limit = int(files_limit_raw)
		except (TypeError, ValueError) as exc:
			raise HTTPException(status_code=400, detail="files_limit must be an integer or null") from exc

	try:
		commit_result = backfill_selected_repositories_commits(
			TEST_USER_ID,
			limit_per_repo=limit_per_repo,
			since_days=since_days,
		)
		files_result = backfill_commit_files(
			TEST_USER_ID,
			limit_commits=files_limit,
		)
		return {"status": "ok", "commits": commit_result, "files": files_result}
	except ValueError as err:
		raise HTTPException(status_code=400, detail=str(err))
	except Exception as err:  # noqa: BLE001
		raise HTTPException(status_code=500, detail=str(err))


@app.get("/health")
def health_check():
	"""Health check endpoint."""
	return {"status": "healthy"}


# Linear OAuth endpoints
@app.get("/auth/linear/start")
def start_linear_oauth():
	"""Initiate Linear OAuth flow."""
	try:
		auth_url, state = build_linear_auth_url(TEST_USER_ID)
		return RedirectResponse(url=auth_url)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error starting OAuth: {str(e)}")


@app.get("/auth/linear/callback")
def linear_callback(code: str, state: str):
	"""Handle Linear OAuth callback."""
	try:
		tokens = exchange_linear_tokens(code, TEST_USER_ID)
		# Redirect back to frontend with success
		return _frontend_redirect("/onboarding?linear=connected")
	except Exception as e:
		# Redirect back to frontend with error
		error_value = quote_plus(str(e))
		return _frontend_redirect(f"/onboarding?error={error_value}")


# Linear data endpoints
@app.get("/linear/teams")
def get_linear_teams():
	"""Fetch Linear teams."""
	try:
		teams_data = fetch_teams(TEST_USER_ID)
		return {
			"status": "success",
			"data": teams_data,
		}
	except ValueError as e:
		raise HTTPException(
			status_code=404,
			detail="Linear integration not connected. Complete OAuth flow first.",
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")


@app.get("/linear/issues")
def get_linear_issues(team_id: str = None, state: str = None, assignee: str = "me"):
	"""Fetch Linear issues with optional filters."""
	try:
		filters = {}
		if state:
			filters["state"] = state
		if assignee:
			filters["assignee"] = assignee

		issues_data = fetch_issues(TEST_USER_ID, team_id=team_id, filters=filters)
		return {
			"status": "success",
			"data": issues_data,
		}
	except ValueError as e:
		raise HTTPException(
			status_code=404,
			detail="Linear integration not connected. Complete OAuth flow first.",
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error fetching issues: {str(e)}")


@app.get("/linear/projects")
def get_linear_projects():
	"""Fetch Linear projects."""
	try:
		projects_data = fetch_projects(TEST_USER_ID)
		return {
			"status": "success",
			"data": projects_data,
		}
	except ValueError as e:
		raise HTTPException(
			status_code=404,
			detail="Linear integration not connected. Complete OAuth flow first.",
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")


@app.post("/linear/issues")
def create_linear_issue(payload: dict):
	"""Create a new Linear issue.

	Request body should include:
	- team_id (required): Team ID
	- title (required): Issue title
	- description (optional): Issue description
	- priority (optional): Priority level (0-4)
	- assignee_id (optional): Assignee user ID
	- state_id (optional): Workflow state ID
	- project_id (optional): Project ID
	"""
	try:
		if "team_id" not in payload or "title" not in payload:
			raise HTTPException(
				status_code=400,
				detail="Missing required fields: team_id and title are required",
			)

		issue_data = create_issue(TEST_USER_ID, **payload)
		return {
			"status": "success",
			"data": issue_data,
		}
	except ValueError as e:
		raise HTTPException(
			status_code=404,
			detail="Linear integration not connected. Complete OAuth flow first.",
		)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error creating issue: {str(e)}")
