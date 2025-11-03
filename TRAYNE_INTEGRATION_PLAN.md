# Trayne OAuth Integration Plan for Ultra Calendar

## Overview

Trayne is a fitness training platform with an OAuth 2.0 provider service. This integration will allow Ultra Calendar users to connect their Trayne account and view their training plans and sessions.

## Architecture

```
Ultra Calendar (YC-Agent-Jam)
    ↓ OAuth Flow
Trayne OAuth Provider (/integrations/external/authorize)
    ↓ Issues Access Token
Ultra Backend stores token
    ↓ API Requests with Bearer token
Trayne Public API (/integrations/external/public-api/*)
    ↓ Returns training data
Ultra displays training plans/sessions
```

## Phase 1: Trayne Setup (Manual Database Configuration)

### 1.1 Register Ultra as OAuth Client in Trayne

**Action**: Insert into Trayne's `oauth_clients` table

**SQL to run in Trayne database:**
```sql
-- Generate client credentials
-- Client ID: ultra-calendar-yc-jam
-- Client Secret: <generate secure random string>

INSERT INTO oauth_clients (
  client_id,
  name,
  description,
  client_secret_hash,
  redirect_uris,
  scopes,
  status,
  created_by
) VALUES (
  'ultra-calendar-yc-jam',
  'Ultra Calendar',
  'YC Agent Jam hackathon project - AI-powered calendar integration',
  '<BCRYPT_HASH_OF_CLIENT_SECRET>',  -- Generate using bcrypt
  ARRAY[
    'http://localhost:8000/auth/trayne/callback',
    'https://ultra-calendar.com/auth/trayne/callback'
  ],
  ARRAY[
    'read:training_plans',
    'read:training_sessions'
  ],
  'active',
  '<YOUR_USER_ID>'  -- Your Trayne user ID
);
```

**Client Secret Generation:**
```bash
# Generate random secret (run this)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Hash it with bcrypt (run this with the secret from above)
python3 -c "import bcrypt; print(bcrypt.hashpw(b'<YOUR_SECRET>', bcrypt.gensalt()).decode())"
```

**Save credentials:**
- Client ID: `ultra-calendar-yc-jam`
- Client Secret: `<plaintext secret from generation>`
- Store these for `.env` configuration

### 1.2 Verify Trayne API Endpoints

**Confirm these endpoints are accessible:**
- `GET https://<trayne-api>/integrations/external/authorize`
- `POST https://<trayne-api>/integrations/external/token`
- `GET https://<trayne-api>/integrations/external/public-api/training-plans`
- `GET https://<trayne-api>/integrations/external/public-api/training-sessions`

**Trayne API Base URL:** `<TODO: Fill in actual Trayne deployment URL>`

## Phase 2: Ultra Backend Implementation

### 2.1 Create Trayne Service (`server/integrations/trayne_service.py`)

**File structure:**
```python
"""Trayne OAuth 2.0 integration service.

Enables Ultra Calendar to connect to Trayne's training platform
and access user workout data via OAuth 2.0.
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Tuple
import requests
from dotenv import load_dotenv

from integrations.supabase_service import get_supabase

load_dotenv()

# Trayne OAuth configuration
TRAYNE_CLIENT_ID = os.environ["TRAYNE_CLIENT_ID"]
TRAYNE_CLIENT_SECRET = os.environ["TRAYNE_CLIENT_SECRET"]
TRAYNE_API_BASE_URL = os.environ["TRAYNE_API_BASE_URL"]
TRAYNE_CALLBACK_URL = os.environ.get("TRAYNE_CALLBACK_URL", "http://localhost:8000/auth/trayne/callback")

# Trayne OAuth endpoints
TRAYNE_AUTH_URL = f"{TRAYNE_API_BASE_URL}/integrations/external/authorize"
TRAYNE_TOKEN_URL = f"{TRAYNE_API_BASE_URL}/integrations/external/token"
TRAYNE_PLANS_URL = f"{TRAYNE_API_BASE_URL}/integrations/external/public-api/training-plans"
TRAYNE_SESSIONS_URL = f"{TRAYNE_API_BASE_URL}/integrations/external/public-api/training-sessions"

# OAuth scopes
DEFAULT_SCOPES = "read:training_plans read:training_sessions"


def build_authorization_url(user_id: str) -> Tuple[str, str]:
    """Generate Trayne OAuth authorization URL.

    Args:
        user_id: Ultra user's UUID

    Returns:
        Tuple of (authorization_url, state_token)
    """
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    params = {
        "client_id": TRAYNE_CLIENT_ID,
        "redirect_uri": TRAYNE_CALLBACK_URL,
        "state": state,
        "scope": DEFAULT_SCOPES,
    }

    query_string = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    auth_url = f"{TRAYNE_AUTH_URL}?{query_string}"

    return auth_url, state


def exchange_code_for_tokens(code: str, user_id: str) -> Dict:
    """Exchange authorization code for access token.

    Args:
        code: Authorization code from Trayne callback
        user_id: Ultra user's UUID

    Returns:
        Token response dict with access_token, expires_in, scope
    """
    supabase = get_supabase()

    # Exchange code for token
    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": TRAYNE_CALLBACK_URL,
        "client_id": TRAYNE_CLIENT_ID,
        "client_secret": TRAYNE_CLIENT_SECRET,
    }

    resp = requests.post(TRAYNE_TOKEN_URL, data=token_payload, timeout=15)
    resp.raise_for_status()
    token_data = resp.json()

    # Calculate expiration (Trayne tokens last 30 days)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    # Store token in database
    supabase.table("trayne_integrations").upsert({
        "user_id": user_id,
        "access_token": token_data["access_token"],
        "scopes": token_data["scope"].split(),
        "expires_at": expires_at.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Update user integration flag
    supabase.table("Users").update({"has_trayne": True}).eq("id", user_id).execute()

    return token_data


def get_access_token(user_id: str) -> str:
    """Get valid access token for user.

    Args:
        user_id: Ultra user UUID

    Returns:
        Valid access token

    Raises:
        ValueError: If no valid token exists
    """
    supabase = get_supabase()
    result = supabase.table("trayne_integrations").select("*").eq("user_id", user_id).execute()

    if not result.data:
        raise ValueError("No Trayne integration found for user")

    token_data = result.data[0]
    expires_at = datetime.fromisoformat(token_data["expires_at"])

    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("Trayne token expired - user must re-authorize")

    return token_data["access_token"]


def fetch_training_plans(user_id: str) -> List[Dict]:
    """Fetch user's training plans from Trayne.

    Args:
        user_id: Ultra user UUID

    Returns:
        List of training plan dicts
    """
    access_token = get_access_token(user_id)

    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(TRAYNE_PLANS_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    plans = resp.json()

    # Cache plans in local database
    supabase = get_supabase()
    for plan in plans:
        supabase.table("trayne_training_plans").upsert({
            "user_id": user_id,
            "trayne_plan_id": plan["id"],
            "name": plan["name"],
            "duration_weeks": plan["duration_weeks"],
            "sessions_per_week": plan["sessions_per_week"],
            "start_date": plan["start_date"],
            "end_date": plan["end_date"],
            "status": plan["status"],
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

    return plans


def fetch_training_sessions(
    user_id: str,
    plan_id: str = None,
    start_date: str = None,
    end_date: str = None
) -> List[Dict]:
    """Fetch user's training sessions from Trayne.

    Args:
        user_id: Ultra user UUID
        plan_id: Filter by training plan ID (optional)
        start_date: Filter start date YYYY-MM-DD (optional)
        end_date: Filter end date YYYY-MM-DD (optional)

    Returns:
        List of training session dicts
    """
    access_token = get_access_token(user_id)

    # Build query params
    params = {}
    if plan_id:
        params["plan_id"] = plan_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(TRAYNE_SESSIONS_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()

    sessions = resp.json()

    # Cache sessions in local database
    supabase = get_supabase()
    for session in sessions:
        supabase.table("trayne_training_sessions").upsert({
            "user_id": user_id,
            "trayne_session_id": session["id"],
            "trayne_plan_id": session["training_plan_id"],
            "name": session["name"],
            "session_type": session["session_type"],
            "scheduled_date": session["scheduled_date"],
            "scheduled_time": session["scheduled_time"],
            "duration_minutes": session["duration_minutes"],
            "status": session["status"],
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

    return sessions
```

### 2.2 Add Routes to `server/app.py`

**Add imports:**
```python
from integrations.trayne_service import (
    build_authorization_url as build_trayne_auth_url,
    exchange_code_for_tokens as exchange_trayne_tokens,
    fetch_training_plans,
    fetch_training_sessions,
)
```

**Add to API info dict (lines 133-154):**
```python
"trayne": {
    "start_oauth": "/auth/trayne/start",
    "callback": "/auth/trayne/callback",
    "fetch_plans": "/trayne/plans",
    "fetch_sessions": "/trayne/sessions",
},
```

**Add OAuth endpoints:**
```python
@app.get("/auth/trayne/start")
def start_trayne_oauth():
    """Initiate Trayne OAuth flow."""
    try:
        auth_url, state = build_trayne_auth_url(TEST_USER_ID)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting OAuth: {str(e)}")


@app.get("/auth/trayne/callback")
def trayne_callback(code: str, state: str):
    """Handle Trayne OAuth callback."""
    try:
        tokens = exchange_trayne_tokens(code, TEST_USER_ID)
        # Redirect back to frontend with success
        return _frontend_redirect("/onboarding?trayne=connected")
    except Exception as e:
        # Redirect back to frontend with error
        error_value = quote_plus(str(e))
        return _frontend_redirect(f"/onboarding?error={error_value}")


@app.get("/trayne/plans")
def get_trayne_plans():
    """Fetch Trayne training plans."""
    try:
        plans_data = fetch_training_plans(TEST_USER_ID)
        return {
            "status": "success",
            "data": plans_data,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail="Trayne integration not connected. Complete OAuth flow first.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching plans: {str(e)}")


@app.get("/trayne/sessions")
def get_trayne_sessions(
    plan_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Fetch Trayne training sessions with optional filters."""
    try:
        sessions_data = fetch_training_sessions(
            TEST_USER_ID,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "status": "success",
            "data": sessions_data,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail="Trayne integration not connected. Complete OAuth flow first.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")
```

### 2.3 Database Schema Changes

**Create migration: `server/supabase/migrations/YYYYMMDD_add_trayne_tables.sql`**

```sql
-- Add has_trayne flag to Users table
ALTER TABLE public.Users
ADD COLUMN IF NOT EXISTS has_trayne boolean NOT NULL DEFAULT false;

-- Create trayne_integrations table
CREATE TABLE IF NOT EXISTS public.trayne_integrations (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL UNIQUE,
    access_token text NOT NULL,
    scopes text[] NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT trayne_integrations_pkey PRIMARY KEY (id),
    CONSTRAINT trayne_integrations_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.Users(id) ON DELETE CASCADE
);

-- Create trayne_training_plans table (cached data)
CREATE TABLE IF NOT EXISTS public.trayne_training_plans (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    trayne_plan_id text NOT NULL,
    name text NOT NULL,
    duration_weeks integer,
    sessions_per_week integer,
    start_date date,
    end_date date,
    status text NOT NULL,
    synced_at timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT trayne_training_plans_pkey PRIMARY KEY (id),
    CONSTRAINT trayne_training_plans_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.Users(id) ON DELETE CASCADE,
    CONSTRAINT trayne_training_plans_unique_user_plan
        UNIQUE (user_id, trayne_plan_id)
);

-- Create trayne_training_sessions table (cached data)
CREATE TABLE IF NOT EXISTS public.trayne_training_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    trayne_session_id text NOT NULL,
    trayne_plan_id text,
    name text NOT NULL,
    session_type text,
    scheduled_date date,
    scheduled_time time,
    duration_minutes integer,
    status text NOT NULL,
    synced_at timestamp with time zone NOT NULL DEFAULT now(),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT trayne_training_sessions_pkey PRIMARY KEY (id),
    CONSTRAINT trayne_training_sessions_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.Users(id) ON DELETE CASCADE,
    CONSTRAINT trayne_training_sessions_unique_user_session
        UNIQUE (user_id, trayne_session_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trayne_integrations_user_id
    ON public.trayne_integrations(user_id);

CREATE INDEX IF NOT EXISTS idx_trayne_plans_user_id
    ON public.trayne_training_plans(user_id);

CREATE INDEX IF NOT EXISTS idx_trayne_plans_status
    ON public.trayne_training_plans(status);

CREATE INDEX IF NOT EXISTS idx_trayne_sessions_user_id
    ON public.trayne_training_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_trayne_sessions_scheduled_date
    ON public.trayne_training_sessions(scheduled_date);

-- Add comments
COMMENT ON TABLE public.trayne_integrations IS
    'Trayne OAuth integration tokens and metadata';

COMMENT ON TABLE public.trayne_training_plans IS
    'Cached training plans from Trayne platform';

COMMENT ON TABLE public.trayne_training_sessions IS
    'Cached training sessions from Trayne platform';
```

### 2.4 Environment Configuration

**Add to `server/.env`:**
```bash
# Trayne Integration
TRAYNE_CLIENT_ID=ultra-calendar-yc-jam
TRAYNE_CLIENT_SECRET=<plaintext secret from Phase 1>
TRAYNE_API_BASE_URL=<Trayne deployment URL>
TRAYNE_CALLBACK_URL=http://localhost:8000/auth/trayne/callback
```

## Phase 3: Frontend Implementation

### 3.1 Update Integration API (`frontend/src/features/onboarding/api/integrationsApi.ts`)

**Add function:**
```typescript
export function startTrayneOAuth(): void {
  withOnboardingReturnHint();
  window.location.href = `${API_BASE_URL}/auth/trayne/start`;
}
```

**Add to exports:**
```typescript
import { startTrayneOAuth } from '../api/integrationsApi';
```

### 3.2 Update Integrations Screen (`frontend/src/features/onboarding/components/IntegrationsScreen.tsx`)

**Update imports (line 6-10):**
```typescript
import {
  startWhoopOAuth,
  startLinearOAuth,
  startGithubOAuth,
  startTrayneOAuth,  // Add this
} from '../api/integrationsApi';
```

**Update handleToggleConnection (line 30-52):**
```typescript
const handleToggleConnection = (id: string) => {
  if (connectedIntegrations.includes(id)) {
    disconnectIntegration(id);
    return;
  }

  if (id === 'whoop') {
    startWhoopOAuth();
    return;
  }

  if (id === 'linear') {
    startLinearOAuth();
    return;
  }

  if (id === 'github') {
    startGithubOAuth();
    return;
  }

  if (id === 'trayne') {  // Add this block
    startTrayneOAuth();
    return;
  }

  connectIntegration(id);
};
```

### 3.3 Update Onboarding Page (`frontend/src/features/onboarding/pages/Onboarding.tsx`)

**Update OAuth callback handler (line 19):**
```typescript
['whoop', 'github', 'linear', 'trayne'].forEach((integrationId) => {
  if (params.get(integrationId) === 'connected') {
    connectIntegration(integrationId);
    shouldReplace = true;
  }
});
```

## Phase 4: Testing Plan

### 4.1 Manual Testing Steps

1. **Trayne OAuth Client Setup**
   - [ ] Run SQL to insert oauth_client in Trayne database
   - [ ] Verify client appears in oauth_clients table
   - [ ] Save client_id and client_secret for .env

2. **Backend Configuration**
   - [ ] Add Trayne credentials to server/.env
   - [ ] Restart backend server
   - [ ] Test `/auth/trayne/start` endpoint in browser
   - [ ] Verify redirect to Trayne authorization page

3. **OAuth Flow**
   - [ ] Log into Trayne account
   - [ ] Authorize Ultra Calendar
   - [ ] Verify redirect back to `/onboarding?trayne=connected`
   - [ ] Check trayne_integrations table for stored token

4. **API Endpoints**
   - [ ] Test `/trayne/plans` - should return training plans
   - [ ] Test `/trayne/sessions` - should return sessions
   - [ ] Verify data cached in trayne_training_plans/sessions tables

5. **Frontend Integration**
   - [ ] Navigate to onboarding integrations screen
   - [ ] Click "Connect" on Trayne card
   - [ ] Complete OAuth flow
   - [ ] Verify "Connected" state shows on card

### 4.2 Error Scenarios to Test

- [ ] Invalid client_id (should fail authorization)
- [ ] Expired token (should show re-authorization needed)
- [ ] User not logged into Trayne (should redirect to login)
- [ ] Network errors during API calls
- [ ] Disconnecting integration (manual token deletion)

## Phase 5: Deployment Checklist

### Production Configuration

1. **Trayne Database**
   - [ ] Add production callback URL to oauth_clients.redirect_uris
   - [ ] Update redirect_uris array: `https://ultra-calendar.com/auth/trayne/callback`

2. **Ultra Backend**
   - [ ] Set production environment variables
   - [ ] Update TRAYNE_CALLBACK_URL in production .env
   - [ ] Run database migrations on production Supabase

3. **Frontend**
   - [ ] Verify API_BASE_URL points to production backend
   - [ ] Test OAuth flow on production domain

## Notes & Considerations

### Security
- Access tokens are stored as plaintext (they're bearer tokens, not passwords)
- Tokens expire after 30 days - no refresh token flow
- User must re-authorize when token expires
- Trayne validates tokens by hashing and checking oauth_access_tokens table

### Data Sync Strategy
- Initial sync on OAuth connection
- Cache training plans and sessions locally
- Provide manual "Sync" button for refresh
- Consider periodic background sync (optional)

### User Experience
- Trayne integration requires existing Trayne account
- Clear messaging: "Connect your Trayne account"
- Handle expired token gracefully with re-auth prompt

### Future Enhancements
- Webhook support for real-time updates
- Write capabilities (mark sessions complete, add notes)
- Richer data display (exercise details, performance metrics)
- Automatic calendar event creation from training sessions

## Implementation Order

1. ✅ Trayne OAuth client registration (manual SQL)
2. Backend service implementation
3. Database migrations
4. Backend route handlers
5. Frontend OAuth flow
6. Testing
7. Production deployment
