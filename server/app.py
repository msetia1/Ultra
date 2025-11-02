import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from integrations.whoop_service import (
	build_authorization_url,
	exchange_code_for_tokens,
	fetch_cycles,
)

load_dotenv()

app = FastAPI(title="AI Scheduling Agent API")

# CORS middleware for frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Serve static files from client directory
client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client")
if os.path.exists(client_path):
	app.mount("/static", StaticFiles(directory=client_path), name="static")

# Development user ID - replace with actual user from auth flow
TEST_USER_ID = os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000000")


@app.get("/")
def root():
	"""Serve the frontend application."""
	client_html = os.path.join(client_path, "index.html")
	if os.path.exists(client_html):
		return FileResponse(client_html)
	return {
		"message": "AI Scheduling Agent API",
		"version": "0.1.0",
		"integrations": {
			"whoop": {
				"start_oauth": "/auth/whoop/start",
				"callback": "/auth/whoop/callback",
				"fetch_cycles": "/whoop/cycles",
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
		},
		"status": "operational",
	}


@app.get("/auth/whoop/start")
def start_whoop_oauth():
	"""Initiate WHOOP OAuth flow."""
	try:
		auth_url, state = build_authorization_url(TEST_USER_ID)
		return RedirectResponse(url=auth_url)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error starting OAuth: {str(e)}")


@app.get("/auth/whoop/callback")
def whoop_callback(code: str, state: str):
	"""Handle WHOOP OAuth callback."""
	try:
		tokens = exchange_code_for_tokens(code, TEST_USER_ID)
		# Redirect back to frontend with success
		return RedirectResponse(url="/?whoop=connected")
	except Exception as e:
		# Redirect back to frontend with error
		return RedirectResponse(url=f"/?error={str(e)}")


@app.get("/whoop/cycles")
def get_whoop_cycles(days: int = 7):
	"""Fetch WHOOP cycle data including recovery, strain, and sleep metrics."""
	try:
		cycles_data = fetch_cycles(TEST_USER_ID, days=days)
		return {
			"status": "success",
			"days_requested": days,
			"data": cycles_data,
		}
	except ValueError as e:
		raise HTTPException(
			status_code=404,
			detail="WHOOP integration not connected. Complete OAuth flow first.",
		)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Error fetching cycles: {str(e)}")


@app.get("/health")
def health_check():
	"""Health check endpoint."""
	return {"status": "healthy"}

